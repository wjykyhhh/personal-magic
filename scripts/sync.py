#!/usr/bin/env python3
"""Fetch one upstream commit into a staging directory; never touches stable."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import urllib.request

from rules import ROOT, dump, git_blob, load_rules, parse, route_checks


def fetch(url, api=False):
    headers = {"User-Agent": "personal-magic-rule-updater"}
    if api and os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(5_000_001)
        if len(data) > 5_000_000:
            raise ValueError("upstream response exceeds 5 MB")
        return data


def main():
    cfg = json.loads((ROOT / "sources.json").read_text())
    old_lock = json.loads((ROOT / "upstream/lock.json").read_text())
    repo = cfg["repository"]
    # Fixed repository; never forward credentials to URLs supplied by a rule file.
    if repo != "blackmatrix7/ios_rule_script" or cfg["branch"] != "master":
        raise ValueError("review updater code before changing the upstream repository")
    ref = json.loads(fetch(f"https://api.github.com/repos/{repo}/git/ref/heads/master", api=True))
    sha = ref["object"]["sha"]
    if sha == old_lock["commit"]:
        print("Upstream commit unchanged")
        return
    new_lock = {"repository": repo, "commit": sha, "files": {}}
    report = ["## Upstream candidate", "", f"Source: https://github.com/{repo}/commit/{sha}", "", "| Category | Added | Removed |", "| --- | ---: | ---: |"]
    changed = False
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp)
        for folder in ("custom", "tests", "upstream"):
            shutil.copytree(ROOT / folder, stage / folder)
        shutil.copy(ROOT / "sources.json", stage / "sources.json")
        for source in cfg["sources"]:
            name, path = source["name"], source["path"]
            if path != f"rule/Clash/{name}/{name}.list":
                raise ValueError("unexpected upstream path")
            data = fetch(f"https://raw.githubusercontent.com/{repo}/{sha}/{path}")
            rows, _ = parse(data.decode("utf-8"), cfg["skip_types"], require_total=True)
            previous = (ROOT / f"upstream/blackmatrix7/{name}.list").read_text()
            old_rows, _ = parse(previous, cfg["skip_types"], require_total=True)
            added, removed = set(rows) - set(old_rows), set(old_rows) - set(rows)
            if len(rows) < source["min_rules"] or max(len(added), len(removed)) / max(len(set(old_rows)), 1) > cfg["max_change_ratio"]:
                raise ValueError(f"{name}: unusually large change; stopped without changing snapshots or stable")
            blob = git_blob(data)
            changed |= blob != old_lock["files"][name]["git_blob_sha"]
            new_lock["files"][name] = {"path": path, "git_blob_sha": blob}
            (stage / f"upstream/blackmatrix7/{name}.list").write_bytes(data)
            report.append(f"| {name} | {len(added)} | {len(removed)} |")
        if not changed:
            print("Selected upstream files unchanged")
            return
        (stage / "upstream/lock.json").write_text(dump(new_lock))
        layers, _ = load_rules(stage)
        route_checks(layers, stage)
        # Commit/push happens only after the complete batch and generated files pass.
        for p in (stage / "upstream").rglob("*"):
            if p.is_file():
                shutil.copy(p, ROOT / p.relative_to(stage))
    report.extend(["", "This is a candidate only. Inspect the diff and test key apps before publishing stable.", "", "Skipped types and policy conflicts are listed in dist/report.json."])
    (ROOT / ".update-report.md").write_text("\n".join(report) + "\n")
    print("Validated candidate snapshots updated; stable was not changed")


if __name__ == "__main__":
    main()
