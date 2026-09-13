import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import rules
import sync


class NativeBaseTests(unittest.TestCase):
    def stage(self, path):
        root = Path(path)
        for folder in ("upstream", "dist", "custom"):
            shutil.copytree(ROOT / folder, root / folder)
        for name in ("sources.json", "routing.json"):
            shutil.copy(ROOT / name, root / name)
        return root

    def tree_bytes(self, root):
        return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}

    def fake_upstream(self, changes=None):
        cfg, contents, _ = rules.load_base()
        contents.update(changes or {})
        directories = {}
        for s in cfg["files"]:
            data = contents[s["path"]]
            m = {"path": s["path"], "sha": rules.git_blob(data), "size": len(data), "type": "file"}
            directories.setdefault(str(Path(s["path"]).parent), []).append(m)
        def fetch(url, api=False):
            if api:
                path = urlsplit(url).path.split("/contents/", 1)[1]
                return json.dumps(directories[path]).encode()
            return contents[url.split("/" + "a" * 40 + "/", 1)[1]]
        return fetch

    def test_published_resources_are_byte_identical(self):
        cfg, contents, report = rules.load_base()
        files = rules.build(check=True)
        self.assertEqual(report["verified_files"], 37)
        self.assertEqual(report["base_files"], 17)
        for item in cfg["files"]:
            if item["role"] == "base":
                self.assertEqual(files[rules.output_path(item)], contents[item["path"]], item["path"])
        self.assertNotIn("quantumultx/rules.list", files)
        self.assertFalse(report["extensions_enabled"])

    def test_native_keyword_asn_process_and_ipv6_are_retained(self):
        files = rules.render()
        self.assertIn(b"HOST-KEYWORD,openai,OpenAI", files["base/QuantumultX/OpenAI/OpenAI.list"])
        self.assertIn(b"IP-ASN,20473,OpenAI", files["base/QuantumultX/OpenAI/OpenAI.list"])
        self.assertIn(b"PROCESS-NAME,", files["base/Clash/Telegram/Telegram_No_Resolve.yaml"])
        self.assertIn(b"IP-CIDR6,", files["base/Clash/Telegram/Telegram_No_Resolve.yaml"])

    def test_all_native_files_are_bound_in_client_adapters(self):
        cfg, _, _ = rules.load_base()
        files = rules.render()
        adapters = {"QuantumultX": files["quantumultx/base.conf"].decode(),
                    "Shadowrocket": files["shadowrocket/personal-magic.conf"].decode(),
                    "Clash": files["clash/providers.yaml"].decode()}
        for item in cfg["files"]:
            if item["role"] == "base":
                self.assertIn(f"{rules.RAW}/{rules.output_path(item)}", adapters[item["client"]])
        sr = adapters["Shadowrocket"]
        for category in ("Global", "China"):
            self.assertIn(f"DOMAIN-SET,{rules.RAW}/base/Shadowrocket/{category}/{category}_Domain.list,", sr)
            self.assertIn(f"RULE-SET,{rules.RAW}/base/Shadowrocket/{category}/{category}.list,", sr)
        link = re.search(r"\]\((https://quantumult.app/[^)]+)\)", files["quantumultx/import.md"].decode())[1]
        resource = json.loads(parse_qs(urlsplit(link).query)["remote-resource"][0])
        self.assertEqual(len(resource["filter_remote"]), 5)
        self.assertEqual(sum("force-policy=proxy," in x for x in resource["filter_remote"]), 4)
        self.assertIn("force-policy=direct,", resource["filter_remote"][-1])
        clash = json.loads(files["clash/providers.yaml"])
        self.assertEqual(len(clash["rule-providers"]), 5)
        for category in cfg["categories"]:
            url = clash["rule-providers"]["pm-" + category.lower()]["url"]
            self.assertEqual(files["clash/" + category.lower() + ".yaml"], files[url.split("/dist/")[1]])

    def test_custom_changes_cannot_affect_base_or_adapters(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as tmp:
            root = self.stage(tmp)
            expected = rules.render(root)
            for path in (root / "custom").iterdir():
                if path.is_file():
                    path.write_text("DOMAIN-SUFFIX,custom-only.example\nmalformed ignored extension draft\n")
            self.assertEqual(expected, rules.render(root))
            shutil.rmtree(root / "custom")
            self.assertEqual(expected, rules.render(root))

    def test_snapshot_and_output_tampering_fail(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as tmp:
            root = self.stage(tmp)
            path = root / "dist/base/QuantumultX/OpenAI/OpenAI.list"
            path.write_bytes(path.read_bytes() + b"# changed newline\r\n")
            with self.assertRaisesRegex(ValueError, "stale generated file"):
                rules.build(check=True, root=root)
            path = rules.snapshot_path(root, "rule/QuantumultX/OpenAI/OpenAI.list")
            path.write_bytes(path.read_bytes() + b"# changed\n")
            with self.assertRaisesRegex(ValueError, "locked Git blob"):
                rules.render(root)

    def test_failed_batch_keeps_all_tracked_files_unchanged(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as tmp:
            root = self.stage(tmp)
            before = self.tree_bytes(root)
            valid_fetch = self.fake_upstream()
            def broken_fetch(url, api=False):
                if not api and url.endswith("/China.list"):
                    return b"<html>download failed</html>"
                return valid_fetch(url, api)
            with patch.object(sync, "fetch", side_effect=broken_fetch):
                with self.assertRaisesRegex(ValueError, "differs from upstream Git blob"):
                    sync.main("a" * 40, root)
            self.assertEqual(before, self.tree_bytes(root))

    def test_valid_update_preserves_remote_bytes_including_crlf(self):
        path = "rule/QuantumultX/OpenAI/OpenAI.list"
        data = rules.snapshot_path(ROOT, path).read_bytes() + b"# upstream annotation\r\n"
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as tmp:
            root = self.stage(tmp)
            with patch.object(sync, "fetch", side_effect=self.fake_upstream({path: data})):
                sync.main("a" * 40, root)
            self.assertEqual(rules.snapshot_path(root, path).read_bytes(), data)
            self.assertEqual((root / "dist/base/QuantumultX/OpenAI/OpenAI.list").read_bytes(), data)
            self.assertEqual(json.loads((root / "upstream/lock.json").read_text())["commit"], "a" * 40)
            rules.build(check=True, root=root)

    def test_large_deletion_is_rejected_without_mutation(self):
        path = "rule/QuantumultX/OpenAI/OpenAI.list"
        lines = rules.snapshot_path(ROOT, path).read_bytes().splitlines(keepends=True)
        data = b"".join(x for i, x in enumerate(lines) if x.startswith(b"#") or i % 2)
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as tmp:
            root = self.stage(tmp)
            before = self.tree_bytes(root)
            with patch.object(sync, "fetch", side_effect=self.fake_upstream({path: data})):
                with self.assertRaisesRegex(ValueError, "unusually large change"):
                    sync.main("a" * 40, root)
            self.assertEqual(before, self.tree_bytes(root))

    def test_missing_shadowrocket_companion_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as tmp:
            root = self.stage(tmp)
            path = "rule/Shadowrocket/Global/Global_Domain.list"
            cfg = json.loads((root / "sources.json").read_text())
            cfg["files"] = [x for x in cfg["files"] if x["path"] != path]
            with patch.object(sync, "fetch", side_effect=self.fake_upstream()):
                with self.assertRaisesRegex(ValueError, "companion domain set"):
                    sync.metadata(cfg, "a" * 40)

    def test_no_scheduled_upstream_updates(self):
        workflow = (ROOT / ".github/workflows/sync.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotRegex(workflow, r"(?m)^\s*(schedule:|-\s*cron:)")


if __name__ == "__main__":
    unittest.main()
