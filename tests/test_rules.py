import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import rules
import sync


class RuleTests(unittest.TestCase):
    def test_bad_downloads_and_unknown_formats_fail(self):
        for text in ("<html>Service unavailable</html>", "", "# TOTAL: 2\nDOMAIN,one.example\n", "# TOTAL: 1\nRULE-SET,https://example.com\n"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    rules.parse(text, require_total=True)

    def test_invalid_network_and_catchall_fail(self):
        for text in ("IP-CIDR,10.1.1.1/8", "IP-CIDR,0.0.0.0/0", "DOMAIN-SUFFIX,*", "DOMAIN,x.com,DIRECT", "DOMAIN-SUFFIX,x.com/evil", "IP-CIDR6,1.1.1.1/32"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                rules.parse(text)

    def test_domain_boundary_and_ipv6(self):
        rows = [("DOMAIN-SUFFIX", "feishu.cn", "DIRECT"), ("IP-CIDR6", "2001:b28:f23c::/47", "PROXY")]
        self.assertEqual(rules.match(rows, "open.feishu.cn"), "DIRECT")
        self.assertIsNone(rules.match(rows, "notfeishu.cn"))
        self.assertIsNone(rules.match(rows, "feishu.cn.evil.com"))
        self.assertEqual(rules.match(rows, "2001:b28:f23d::1"), "PROXY")

    def test_real_routes_and_generated_files(self):
        files = rules.build(check=True)
        qx = files["quantumultx/rules.list"]
        self.assertNotIn("no-resolve", qx)
        self.assertIn("ip6-cidr,", qx)
        self.assertTrue(qx.endswith("geoip,cn,direct\nfinal,proxy\n"))
        self.assertNotIn("[MITM]", files["shadowrocket/personal-magic.conf"])
        # Decode each target back to routing triples and check the same cases.
        datasets = []
        mapping = {"host": "DOMAIN", "host-suffix": "DOMAIN-SUFFIX", "ip-cidr": "IP-CIDR", "ip6-cidr": "IP-CIDR6"}
        datasets.append([(mapping[p[0]], p[1], p[2].upper()) for l in qx.splitlines() if (p := l.split(","))[0] in mapping])
        sr = files["shadowrocket/personal-magic.conf"].split("[Rule]\n")[1]
        datasets.append([tuple(l.split(",")[:3]) for l in sr.splitlines() if l.startswith(tuple(rules.SUPPORTED))])
        clash = files["clash/rules.yaml"]
        datasets.append([tuple(json.loads(l[4:]).split(",")[:3]) for l in clash.splitlines() if l.startswith("  - ") and json.loads(l[4:]).split(",")[0] in rules.SUPPORTED])
        providers = json.loads(files["clash/providers.yaml"])
        decoded = []
        for rule in providers["rules"]:
            p = rule.split(",")
            if p[0] != "RULE-SET":
                continue
            filename = providers["rule-providers"][p[1]]["url"].split("/dist/")[1]
            decoded.extend((*json.loads(l[4:]).split(",")[:2], p[2]) for l in files[filename].splitlines() if l.startswith("  - "))
        datasets.append(decoded)
        for dataset in datasets:
            for case in json.loads((ROOT / "tests/routes.json").read_text()):
                self.assertEqual(rules.match(dataset, case["host"]), case["policy"], case["host"])

    def test_snapshot_tampering_and_custom_conflict_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for folder in ("custom", "upstream", "tests"):
                shutil.copytree(ROOT / folder, root / folder)
            shutil.copy(ROOT / "sources.json", root / "sources.json")
            p = root / "custom/proxy.list"
            p.write_text(p.read_text() + "DOMAIN-SUFFIX,feishu.cn\n")
            with self.assertRaisesRegex(ValueError, "conflict"):
                rules.load_rules(root)
            shutil.copy(ROOT / "custom/proxy.list", p)
            with (root / "upstream/blackmatrix7/Global.list").open("a") as f:
                f.write("DOMAIN-SUFFIX,tampered.example\n")
            with self.assertRaisesRegex(ValueError, "locked Git blob"):
                rules.load_rules(root)

    def test_upstream_batch_failure_leaves_snapshots_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for folder in ("custom", "upstream", "tests"):
                shutil.copytree(ROOT / folder, root / folder)
            shutil.copy(ROOT / "sources.json", root / "sources.json")
            before = {p: p.read_bytes() for p in (root / "upstream").rglob("*") if p.is_file()}
            # First download is valid, second fails: even the first must not be installed.
            responses = [json.dumps({"object": {"sha": "a" * 40}}).encode(),
                         (root / "upstream/blackmatrix7/OpenAI.list").read_bytes(),
                         b"<html>upstream failure</html>"]
            with patch.object(sync, "ROOT", root), patch.object(sync, "fetch", side_effect=responses):
                with self.assertRaises(ValueError):
                    sync.main()
            self.assertEqual(before, {p: p.read_bytes() for p in before})
            self.assertFalse((root / ".update-report.md").exists())

    def test_large_upstream_deletion_is_rejected(self):
        text = (ROOT / "upstream/blackmatrix7/OpenAI.list").read_text()
        lines = text.splitlines()
        removed = 0
        kept = []
        for line in lines:
            if line.startswith("DOMAIN-SUFFIX,") and removed < 10:
                removed += 1
            else:
                kept.append(line.replace("# TOTAL: 35", "# TOTAL: 25"))
        responses = [json.dumps({"object": {"sha": "b" * 40}}).encode(), ("\n".join(kept) + "\n").encode()]
        with patch.object(sync, "fetch", side_effect=responses):
            with self.assertRaisesRegex(ValueError, "unusually large change"):
                sync.main()


if __name__ == "__main__":
    unittest.main()
