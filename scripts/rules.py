#!/usr/bin/env python3
"""Offline, deterministic routing compiler. Python 3.11+, standard library only."""
import argparse
from collections import Counter
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import sys
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
REPO = "wjykyhhh/personal-magic"
RAW = f"https://raw.githubusercontent.com/{REPO}/stable/dist"
SUPPORTED = {"DOMAIN", "DOMAIN-SUFFIX", "IP-CIDR", "IP-CIDR6"}


def dump(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def git_blob(data):
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def parse(text, skipped=None, require_total=False):
    skipped = skipped or {}
    rows, ignored, counts = [], Counter(), Counter()
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith(("#", ";", "//")):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) not in (2, 3) or not parts[1]:
            raise ValueError(f"line {n}: malformed rule: {line[:100]}")
        kind, value = parts[:2]
        counts[kind] += 1
        if kind in skipped:
            if len(parts) == 3 and (kind != "IP-ASN" or parts[2] != "no-resolve"):
                raise ValueError(f"line {n}: unexpected option")
            ignored[kind] += 1
            continue
        if kind not in SUPPORTED:
            raise ValueError(f"line {n}: unsupported type {kind}")
        if kind.startswith("IP-CIDR"):
            if len(parts) == 3 and parts[2] != "no-resolve":
                raise ValueError(f"line {n}: unexpected IP option")
            net = ipaddress.ip_network(value, strict=True)
            if net.prefixlen == 0:
                raise ValueError("default routes must only appear in the generated fallback")
            if kind == "IP-CIDR6" and net.version != 6:
                raise ValueError("IP-CIDR6 needs IPv6")
            kind = "IP-CIDR6" if net.version == 6 else "IP-CIDR"
            value = str(net)
        else:
            if len(parts) != 2:
                raise ValueError(f"line {n}: policies do not belong in source lists")
            value = value.lower().encode("idna").decode("ascii")
            if len(value) > 253 or any(not re.fullmatch(r"[a-z0-9_](?:[a-z0-9_-]{0,61}[a-z0-9_])?", p) for p in value.split(".")):
                raise ValueError(f"line {n}: invalid domain {value}")
        rows.append((kind, value))
    if require_total:
        totals = re.findall(r"^# TOTAL: (\d+)\s*$", text, re.M)
        if len(totals) != 1 or int(totals[0]) != sum(counts.values()):
            raise ValueError(f"header TOTAL disagrees with actual rules ({sum(counts.values())})")
    return rows, dict(ignored)


def load_rules(root=ROOT):
    cfg = json.loads((root / "sources.json").read_text())
    lock = json.loads((root / "upstream/lock.json").read_text())
    if lock["repository"] != cfg["repository"] or not re.fullmatch(r"[0-9a-f]{40}", lock["commit"]):
        raise ValueError("invalid upstream lock")
    layers, report = [], {"upstream_commit": lock["commit"], "sources": {}, "overrides": []}
    custom = {}
    for name in ("lan", "direct", "proxy", "exclude"):
        custom[name], _ = parse((root / f"custom/{name}.list").read_text())
    conflicts = set(custom["direct"]) & set(custom["proxy"])
    if conflicts:
        raise ValueError(f"custom direct/proxy conflict: {sorted(conflicts)}")
    layers.extend([("lan", "DIRECT", custom["lan"]), ("custom-direct", "DIRECT", custom["direct"]), ("custom-proxy", "PROXY", custom["proxy"])])
    exclude = set(custom["exclude"])
    for source in cfg["sources"]:
        name = source["name"]
        data = (root / f"upstream/blackmatrix7/{name}.list").read_bytes()
        expected = lock["files"][name]
        if source["path"] != expected["path"] or git_blob(data) != expected["git_blob_sha"]:
            raise ValueError(f"{name}: snapshot does not match the locked Git blob")
        rows, skipped = parse(data.decode("utf-8"), cfg["skip_types"], require_total=True)
        if len(rows) < source["min_rules"]:
            raise ValueError(f"{name}: suspiciously few rules")
        report["sources"][name] = {"accepted": len(rows), "skipped": skipped, "excluded": len(set(rows) & exclude)}
        layers.append((name.lower(), source["policy"], [r for r in rows if r not in exclude]))
    # First exact rule wins; do not sort across policy layers.
    seen, compiled = {}, []
    for name, policy, rows in layers:
        accepted = []
        for row in rows:
            if row in seen:
                if seen[row] != policy:
                    report["overrides"].append({"rule": ",".join(row), "kept": seen[row], "ignored": policy, "source": name})
                continue
            seen[row] = policy
            accepted.append(row)
        compiled.append((name, policy, accepted))
    report["total_rules"] = len(seen)
    return compiled, report


def flatten(layers):
    return [(kind, value, policy) for _, policy, rows in layers for kind, value in rows]


def match(rows, host):
    """Offline explicit-rule check. Does not query DNS or simulate the GeoIP database."""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    host = host.lower().rstrip(".")
    for kind, value, policy in rows:
        if address is not None:
            if kind.startswith("IP-CIDR") and address in ipaddress.ip_network(value):
                return policy
        elif kind == "DOMAIN" and host == value:
            return policy
        elif kind == "DOMAIN-SUFFIX" and (host == value or host.endswith("." + value)):
            return policy
    return None


def route_checks(layers, root=ROOT):
    rows = flatten(layers)
    cases = json.loads((root / "tests/routes.json").read_text())
    for case in cases:
        actual = match(rows, case["host"])
        if actual != case["policy"]:
            raise ValueError(f"route regression: {case['host']} expected {case['policy']}, got {actual}")
    return len(cases)


def render(root=ROOT):
    layers, report = load_rules(root)
    report["route_checks"] = route_checks(layers, root)
    rows = flatten(layers)
    fingerprint = hashlib.sha256(dump(rows).encode()).hexdigest()
    report["rules_sha256"] = fingerprint
    header = f"# personal-magic | rules {fingerprint[:16]}\n# GPL-2.0 | sources and modifications: https://github.com/{REPO}\n"
    qx_types = {"DOMAIN": "host", "DOMAIN-SUFFIX": "host-suffix", "IP-CIDR": "ip-cidr", "IP-CIDR6": "ip6-cidr"}
    # QX uses its own IP matching behavior; Surge/Clash no-resolve is not copied.
    qx = [f"{qx_types[k]},{v},{p.lower()}" for k, v, p in rows]
    sr = [f"{'IP-CIDR' if k == 'IP-CIDR6' else k},{v},{p}" + (",no-resolve" if k.startswith("IP-CIDR") else "") for k, v, p in rows]
    clash = [f"{k},{v},{p}" + (",no-resolve" if k.startswith("IP-CIDR") else "") for k, v, p in rows]
    files = {
        "quantumultx/rules.list": header + "\n".join(qx + ["geoip,cn,direct", "final,proxy"]) + "\n",
        "shadowrocket/personal-magic.conf": header + """
[General]
dns-server = https://doh.pub/dns-query,https://dns.alidns.com/dns-query
fallback-dns-server = system
ipv6 = true
prefer-ipv6 = false
dns-direct-fallback-proxy = false
private-ip-answer = true
udp-policy-not-supported-behaviour = REJECT

[Rule]
""" + "\n".join(sr + ["GEOIP,CN,DIRECT", "FINAL,PROXY"]) + "\n",
        "clash/rules.yaml": header + "# Merge the rules key into an existing config; PROXY must be an existing policy group.\nrules:\n" + "".join("  - " + json.dumps(r) + "\n" for r in clash + ["GEOIP,CN,DIRECT", "MATCH,PROXY"]),
        "report.json": dump(report),
    }
    providers = {}
    provider_rules = []
    for name, policy, entries in layers:
        if not entries:
            continue
        payload = [f"{k},{v}" + (",no-resolve" if k.startswith("IP-CIDR") else "") for k, v in entries]
        files[f"clash/{name}.yaml"] = header + "payload:\n" + "".join("  - " + json.dumps(r) + "\n" for r in payload)
        providers[f"pm-{name}"] = {"type": "http", "behavior": "classical", "format": "yaml", "url": f"{RAW}/clash/{name}.yaml", "path": f"./ruleset/personal-magic/{name}.yaml", "interval": 86400}
        provider_rules.append(f"RULE-SET,pm-{name},{policy}")
    # JSON is valid YAML; keeps this compiler dependency-free.
    files["clash/providers.yaml"] = dump({"rule-providers": providers, "rules": provider_rules + ["GEOIP,CN,DIRECT", "MATCH,PROXY"]})
    resource = f"{RAW}/quantumultx/rules.list, tag=personal-magic, update-interval=86400, opt-parser=false, enabled=true"
    link = "https://quantumult.app/x/open-app/add-resource?remote-resource=" + quote(json.dumps({"filter_remote": [resource]}, separators=(",", ":")), safe="")
    files["quantumultx/import.md"] = f"# Quantumult X\n\n[添加 personal-magic 分流订阅]({link})\n\n这是添加分流资源，不会替你整理已有规则。保留节点订阅，停用其他重叠分流资源，检查本地规则是否覆盖本资源。不要设置 force-policy；资源内混合了 direct/proxy。选择分流模式，并选择可用的代理节点。\n\n手工添加至 `[filter_remote]`：\n\n```ini\n{resource}\n```\n"
    files["checksums.json"] = dump({p: hashlib.sha256(v.encode()).hexdigest() for p, v in sorted(files.items())})
    return files


def build(check=False, root=ROOT):
    files = render(root)
    dest = root / "dist"
    if check:
        actual = {str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file()}
        if actual != set(files):
            raise ValueError("dist file set is stale; run python scripts/rules.py build")
        for name, content in files.items():
            if (dest / name).read_bytes() != content.encode():
                raise ValueError(f"stale generated file: dist/{name}")
    else:
        for p in dest.rglob("*"):
            if p.is_file() and str(p.relative_to(dest)) not in files:
                p.unlink()
        for name, content in files.items():
            p = dest / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content.encode())
    return files


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build", "check", "match"])
    parser.add_argument("host", nargs="?")
    args = parser.parse_args()
    try:
        if args.command == "match":
            if not args.host:
                parser.error("match requires a hostname or IP")
            layers, _ = load_rules()
            print(match(flatten(layers), args.host) or "No explicit match: client GeoIP CN, then PROXY")
        else:
            files = build(check=args.command == "check")
            report = json.loads(files["report.json"])
            print(f"OK: {report['total_rules']} rules, {report['route_checks']} routing checks, {len(files)} generated files")
    except (ValueError, KeyError, OSError) as exc:
        sys.exit(str(exc))
