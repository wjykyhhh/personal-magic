#!/usr/bin/env python3
"""Verify/copy native upstream bytes; generate only client subscription adapters."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
REPO = "wjykyhhh/personal-magic"
RAW = f"https://raw.githubusercontent.com/{REPO}/stable/dist"
UPSTREAM = "blackmatrix7/ios_rule_script"


def dump(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def git_blob(data):
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def snapshot_path(root, path):
    return root / "upstream/blackmatrix7" / path


def output_path(source):
    return "base/" + source["path"].removeprefix("rule/")


def entries(data, format):
    """Count/diff only. These strings are NEVER used to produce rule files."""
    rows = [line.strip() for line in data.decode("utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith(("#", ";", "//"))]
    if format == "classical":
        if not rows or rows[0] != "payload:" or any(not x.startswith("- ") for x in rows[1:]):
            raise ValueError("invalid classical YAML payload")
        rows = rows[1:]
    if format != "markdown" and (not rows or any("<html" in x.lower() or "<!doctype" in x.lower() for x in rows)):
        raise ValueError("empty rule file or HTML response")
    return rows


def read_config(root=ROOT):
    cfg = json.loads((root / "sources.json").read_text())
    if cfg["schema_version"] != 2 or cfg["repository"] != UPSTREAM or cfg["branch"] != "master":
        raise ValueError("unexpected upstream configuration")
    seen = set()
    for item in cfg["files"]:
        path = PurePosixPath(item["path"])
        if (str(path) != item["path"] or len(path.parts) != 4 or path.parts[0] != "rule"
                or path.parts[1] != item["client"] or path.parts[2] != item["category"]
                or any(p in ("..", ".") for p in path.parts)
                or item["client"] not in ("QuantumultX", "Shadowrocket", "Clash")
                or item["category"] not in cfg["categories"] or str(path) in seen
                or item["role"] not in ("base", "reference")
                or item["format"] not in ("qx", "rule-set", "domain-set", "classical", "markdown")):
            raise ValueError(f"invalid/duplicate source path: {path}")
        seen.add(str(path))
    return cfg


def load_base(root=ROOT):
    cfg = read_config(root)
    lock = json.loads((root / "upstream/lock.json").read_text())
    if lock["repository"] != UPSTREAM or not re.fullmatch(r"[0-9a-f]{40}", lock["commit"]):
        raise ValueError("invalid upstream lock")
    expected = {item["path"] for item in cfg["files"]}
    actual = {str(p.relative_to(root / "upstream/blackmatrix7"))
              for p in (root / "upstream/blackmatrix7").rglob("*") if p.is_file()}
    if set(lock["files"]) != expected or actual != expected:
        raise ValueError("snapshot/manifest file set differs from sources.json")
    contents = {}
    report = {"mode": "native-upstream-base", "scope": "selected categories, not entire upstream repository",
              "categories": cfg["categories"], "upstream_commit": lock["commit"],
              "extensions_enabled": False, "transformed_rules": 0, "files": {}}
    for item in cfg["files"]:
        path = item["path"]
        data = snapshot_path(root, path).read_bytes()
        meta = lock["files"][path]
        if len(data) != meta["size"] or git_blob(data) != meta["git_blob_sha"]:
            raise ValueError(f"{path}: snapshot does not match the locked Git blob")
        rows = entries(data, item["format"])
        contents[path] = data
        if item["role"] == "base":
            report["files"][path] = {"git_blob_sha": meta["git_blob_sha"], "bytes": len(data),
                                     "entries": len(rows), "output": "dist/" + output_path(item)}
    report["rules_sha256"] = hashlib.sha256(dump(report["files"]).encode()).hexdigest()
    report["verified_files"] = len(contents)
    report["base_files"] = len(report["files"])
    return cfg, contents, report


def render(root=ROOT):
    cfg, contents, report = load_base(root)
    routing = json.loads((root / "routing.json").read_text())
    if set(routing) != {"category_order", "policies", "geoip_cn", "final"}:
        raise ValueError("review adapter code before adding routing options")
    if (routing["category_order"] != cfg["categories"] or set(routing["policies"]) != set(cfg["categories"])
            or any(v not in ("DIRECT", "PROXY") for v in routing["policies"].values())
            or routing["geoip_cn"] != "DIRECT" or routing["final"] != "PROXY"):
        raise ValueError("invalid adapter policy bindings")
    files = {output_path(item): contents[item["path"]] for item in cfg["files"] if item["role"] == "base"}
    header = "# personal-magic client adapter; upstream rule bytes are in dist/base/\n# Custom extensions are disabled. Policy bindings/fallbacks are local choices.\n"
    resources, sr_rules, providers, clash_rules = [], [], {}, []
    for category in routing["category_order"]:
        policy = routing["policies"][category]
        for client, formats in (("QuantumultX", ["qx"]), ("Shadowrocket", ["domain-set", "rule-set"]), ("Clash", ["classical"])):
            selected = [s for s in cfg["files"] if s["role"] == "base" and s["category"] == category and s["client"] == client]
            if not selected or any(s["format"] not in formats for s in selected):
                raise ValueError(f"missing/invalid native resource: {client}/{category}")
            # Upstream Shadowrocket large sets intentionally split domains/IP rules.
            if client == "Shadowrocket" and category in ("Global", "China") and {s["format"] for s in selected} != set(formats):
                raise ValueError(f"missing companion domain set: {category}")
            for s in sorted(selected, key=lambda s: formats.index(s["format"])):
                url = f"{RAW}/{output_path(s)}"
                if client == "QuantumultX":
                    resources.append(f"{url}, tag=pm-base-{category}, force-policy={policy.lower()}, update-interval=86400, opt-parser=false, enabled=true")
                elif client == "Shadowrocket":
                    sr_rules.append(f"{s['format'].upper()},{url},{policy}")
                else:
                    name = f"pm-{category.lower()}"
                    providers[name] = {"type": "http", "behavior": "classical", "format": "yaml", "url": url,
                                       "path": f"./ruleset/personal-magic/base/{category}.yaml", "interval": 86400}
                    clash_rules.append(f"RULE-SET,{name},{policy}")
                    # Keep these older per-category URLs, now as exact upstream bytes.
                    files[f"clash/{category.lower()}.yaml"] = contents[s["path"]]
    qx_config = header + "[filter_remote]\n" + "\n".join(resources) + "\n\n[filter_local]\ngeoip,cn,direct\nfinal,proxy\n"
    files["quantumultx/base.conf"] = qx_config.encode()
    link = "https://quantumult.app/x/open-app/add-resource?remote-resource=" + quote(json.dumps({"filter_remote": resources}, separators=(",", ":")), safe="")
    import_doc = f"""# Quantumult X 原版基础

[一键添加五组原版分流资源]({link})

**从旧版迁移：先停用旧的 `personal-magic` 混合分流资源，再添加本页五组资源。旧的 `dist/quantumultx/rules.list` 已撤下，刷新旧链接不能完成迁移。**

保留节点订阅，选择分流模式和可用节点。添加链接只追加分流资源，不会清理旧资源或修改本地规则。

每组文件与固定版本的 blackmatrix7 原生 QX 文件逐字节一致，保留原有类别名策略。这里用资源的 `force-policy` 绑定：OpenAI、Twitter、Telegram、Global → `proxy`，China → `direct`。不要移除该绑定，否则需自行建立同名策略。

以下是合并片段，不是整份 QX 配置。将 `[filter_remote]` 的行加入现有对应区段；检查原有 `[filter_local]`，在其中设置末尾兜底（相同区段不要重复建）。一键添加不会设置兜底。

```ini
{qx_config}```

`geoip` / `final` 是本项目的兜底选择，属于接入配置，不属于上游原始规则。客户端本地规则及其他资源仍可能影响实际匹配。

自定义飞书、银行、Grok、Typeless 等补充当前未启用；实际覆盖以这五组原版文件为准。仓库不自动同步上游；资源每 24 小时只检查已发布的 stable，亦可手工刷新。
"""
    files["quantumultx/import.md"] = import_doc.encode()
    sr = header + """
[General]
dns-server = https://doh.pub/dns-query,https://dns.alidns.com/dns-query
fallback-dns-server = system
ipv6 = true
prefer-ipv6 = false
dns-direct-fallback-proxy = false
private-ip-answer = true
udp-policy-not-supported-behaviour = REJECT

[Rule]
""" + "\n".join(sr_rules + ["GEOIP,CN,DIRECT", "FINAL,PROXY"]) + "\n"
    files["shadowrocket/personal-magic.conf"] = sr.encode()
    clash = dump({"rule-providers": providers, "rules": clash_rules + ["GEOIP,CN,DIRECT", "MATCH,PROXY"]}).encode()
    files["clash/providers.yaml"] = clash
    files["clash/rules.yaml"] = clash
    report["adapter_policies"] = routing
    report["retired_urls"] = ["dist/quantumultx/rules.list", "dist/clash/lan.yaml", "dist/clash/custom-direct.yaml", "dist/clash/custom-proxy.yaml"]
    files["report.json"] = dump(report).encode()
    files["checksums.json"] = dump({p: hashlib.sha256(v).hexdigest() for p, v in sorted(files.items())}).encode()
    return files


def build(check=False, root=ROOT):
    files = render(root)
    dest = root / "dist"
    actual = {str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file()}
    if check:
        if actual != set(files):
            raise ValueError("dist file set is stale; run python3 scripts/rules.py build")
        for name, data in files.items():
            if (dest / name).read_bytes() != data:
                raise ValueError(f"stale generated file: dist/{name}")
    else:
        for name in actual - set(files):
            (dest / name).unlink()
        for name, data in files.items():
            p = dest / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
    return files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "check"])
    args = parser.parse_args()
    try:
        files = build(check=args.command == "check")
        report = json.loads(files["report.json"])
        print(f"OK: {report['verified_files']} verified upstream files; {report['base_files']} byte-identical native resources; extensions disabled")
    except (ValueError, KeyError, OSError) as exc:
        sys.exit(str(exc))
