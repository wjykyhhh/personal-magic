import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import library
import rules
import sync


class LibraryTests(unittest.TestCase):
    def test_tree_hash_matches_git_including_names_modes_and_bytes(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as tmp:
            root = Path(tmp)
            (root / "rule/ab").mkdir(parents=True)
            (root / "rule/ab/a.list").write_bytes(b"# original\r\nHOST,duplicate,Policy\nHOST,duplicate,Policy\n")
            (root / "rule/ab.txt").write_bytes(bytes(range(256)))
            (root / "rule/中文.list").write_bytes(b"arbitrary new format\n")
            script = root / "rule/ab/executable"
            script.write_bytes(b"#!/bin/sh\n")
            script.chmod(0o755)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "-c", "core.autocrlf=false", "add", "rule"], check=True)
            expected = subprocess.check_output(["git", "-C", str(root), "write-tree", "--prefix=rule/"], text=True).strip()
            actual, manifest = library.scan_library(root / "rule")
            self.assertEqual(actual, expected)
            self.assertEqual(len(manifest), 4)

    def test_archive_rejects_escape_and_symlinks(self):
        for name, kind in (("../escape", tarfile.REGTYPE), ("rule/link", tarfile.SYMTYPE)):
            with self.subTest(name=name), tempfile.TemporaryDirectory(dir=ROOT.parent) as tmp:
                root = Path(tmp)
                archive = root / "test.tar"
                with tarfile.open(archive, "w") as tar:
                    member = tarfile.TarInfo(name)
                    member.type = kind
                    member.linkname = "../../escape" if kind == tarfile.SYMTYPE else ""
                    tar.addfile(member, io.BytesIO(b""))
                with self.assertRaises(ValueError):
                    sync.extract_archive(archive, root / "out")
                self.assertFalse((root / "escape").exists())

    def test_full_manifest_detects_extra_missing_and_changed_files(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as tmp:
            root = Path(tmp)
            directory = root / "upstream/blackmatrix7/rule/NewClient/NewCategory"
            directory.mkdir(parents=True)
            path = directory / "all.rules"
            path.write_bytes(b"new format kept unchanged\r\n")
            tree, files = library.scan_library(root / "upstream/blackmatrix7/rule")
            lock = {"schema_version": 3, "scope": "complete rule/ directory", "rule_tree_sha": tree, "files": files}
            self.assertEqual(library.verify_library(root, lock)["file_count"], 1)
            path.write_bytes(b"modified")
            with self.assertRaises(ValueError):
                library.verify_library(root, lock)
            path.unlink()
            with self.assertRaises(ValueError):
                library.verify_library(root, lock)
            path.write_bytes(b"new format kept unchanged\r\n")
            (directory / "extra").write_bytes(b"extra")
            with self.assertRaises(ValueError):
                library.verify_library(root, lock)


class PublishedBaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = rules.build(check=True)
        cls.report = json.loads(cls.files["report.json"])
        cls.cfg = rules.read_config()
        cls.lock = json.loads((ROOT / "upstream/lock.json").read_text())

    def test_complete_library_and_selected_adapter_files(self):
        self.assertEqual(self.report["verified_files"], len(self.lock["files"]))
        self.assertGreater(self.report["verified_files"], len(self.cfg["files"]))
        self.assertTrue({"AdGuard", "Clash", "Loon", "QuantumultX", "Shadowrocket", "Surge"} <= set(self.report["library"]["client_files"]))
        self.assertEqual(self.report["library"]["rule_tree_sha"], self.lock["rule_tree_sha"])
        for item in self.cfg["files"]:
            if item["role"] == "base":
                self.assertEqual(self.files[rules.output_path(item)], rules.snapshot_path(ROOT, item["path"]).read_bytes())
        self.assertFalse(self.report["extensions_enabled"])

    def test_native_types_and_companion_sets_are_preserved(self):
        self.assertIn(b"HOST-KEYWORD,openai,OpenAI", self.files["base/QuantumultX/OpenAI/OpenAI.list"])
        self.assertIn(b"IP-ASN,20473,OpenAI", self.files["base/QuantumultX/OpenAI/OpenAI.list"])
        self.assertIn(b"PROCESS-NAME,", self.files["base/Clash/Telegram/Telegram_No_Resolve.yaml"])
        sr = self.files["shadowrocket/personal-magic.conf"].decode()
        for category in ("Global", "China"):
            self.assertIn(f"DOMAIN-SET,{rules.RAW}/base/Shadowrocket/{category}/{category}_Domain.list,", sr)
            self.assertIn(f"RULE-SET,{rules.RAW}/base/Shadowrocket/{category}/{category}.list,", sr)

    def test_qx_profile_is_explicitly_a_selection(self):
        doc = self.files["quantumultx/import.md"].decode()
        link = re.search(r"\]\((https://quantumult.app/[^)]+)\)", doc)[1]
        remote = json.loads(parse_qs(urlsplit(link).query)["remote-resource"][0])["filter_remote"]
        self.assertEqual(len(remote), 5)
        self.assertEqual(sum("force-policy=proxy," in x for x in remote), 4)
        self.assertIn("force-policy=direct,", remote[-1])
        self.assertIn("完整规则库", doc)

    def test_custom_drafts_are_never_read(self):
        original = Path.read_bytes
        def guarded(path):
            if "custom" in path.parts:
                raise AssertionError("base builder read a custom extension")
            return original(path)
        with patch.object(Path, "read_bytes", guarded):
            self.assertEqual(rules.render(), self.files)

    def test_failed_acquisition_cannot_modify_repository(self):
        # Small, valid old selected snapshot exercises the complete-library migration.
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as tmp:
            root = Path(tmp)
            for name in ("sources.json", "routing.json"):
                shutil.copyfile(ROOT / name, root / name)
            old = {"schema_version": 2, "repository": rules.UPSTREAM, "commit": self.lock["commit"], "files": {}}
            for item in self.cfg["files"]:
                path = item["path"]
                data = rules.snapshot_path(ROOT, path).read_bytes()
                dest = rules.snapshot_path(root, path)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                old["files"][path] = {"size": len(data), "git_blob_sha": rules.git_blob(data)}
            (root / "upstream/lock.json").write_text(rules.dump(old))
            (root / "dist").mkdir()
            (root / "dist/keep").write_bytes(b"existing subscription")
            before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            with patch.object(sync, "acquire", side_effect=ValueError("failed acquisition")):
                with self.assertRaisesRegex(ValueError, "failed acquisition"):
                    sync.main("a" * 40, root=root)
            self.assertEqual(before, {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()})

    def test_no_scheduled_updates(self):
        for path in (ROOT / ".github/workflows").glob("*.yml"):
            self.assertNotRegex(path.read_text(), r"(?m)^\s*(schedule:|-\s*cron:)")
        workflow = (ROOT / ".github/workflows/sync.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotRegex(workflow, r"(?m)^\s*push:")


if __name__ == "__main__":
    unittest.main()
