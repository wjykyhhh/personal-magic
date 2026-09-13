#!/usr/bin/env python3
"""Manually stage exact native files from one upstream commit; never publish stable."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import urllib.request

from rules import ROOT, UPSTREAM, build, dump, entries, git_blob, load_base, snapshot_path


def fetch(url, api=False):
    headers = {"User-Agent": "personal-magic-native-updater"}
    if api and os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read(5_000_001)
        if len(data) > 5_000_000:
            raise ValueError("upstream response exceeds 5 MB")
        return data


def metadata(cfg, sha):
    directories = sorted({str(Path(s["path"]).parent) for s in cfg["files"]})
    def directory(path):
        result = json.loads(fetch(f"https://api.github.com/repos/{UPSTREAM}/contents/{path}?ref={sha}", api=True))
        if not isinstance(result, list):
            raise ValueError(f"invalid upstream directory: {path}")
        return result
    with ThreadPoolExecutor(max_workers=5) as pool:
        batches = list(pool.map(directory, directories))
    remote = {s["path"]: s for batch in batches for s in batch}
    selected = {s["path"] for s in cfg["files"] if s["role"] == "base"}
    for category in cfg["categories"]:
        companion = f"rule/Shadowrocket/{category}/{category}_Domain.list"
        if companion in remote and companion not in selected:
            raise ValueError(f"new companion domain set: {companion}; update sources.json before syncing")
    for s in cfg["files"]:
        m = remote.get(s["path"], {})
        if m.get("type") != "file" or not re.fullmatch(r"[0-9a-f]{40}", m.get("sha", "")) or not 0 < m.get("size", 0) <= 5_000_000:
            raise ValueError(f"missing/invalid upstream file: {s['path']}")
    return remote


def validate_download(source, data, meta, previous, ratio):
    if len(data) != meta["size"] or git_blob(data) != meta["sha"]:
        raise ValueError(f"{source['path']}: download differs from upstream Git blob")
    current = entries(data, source["format"])
    if source["format"] == "markdown":
        return 0, 0
    old = Counter(entries(previous, source["format"]))
    new = Counter(current)
    added, removed = sum((new - old).values()), sum((old - new).values())
    if max(added, removed) / max(sum(old.values()), 1) > ratio:
        raise ValueError(f"{source['path']}: unusually large change; snapshots/stable unchanged")
    return added, removed


def main(commit=None, root=None):
    root = root or ROOT
    cfg, old_contents, old_report = load_base(root)
    if commit is None:
        ref = json.loads(fetch(f"https://api.github.com/repos/{UPSTREAM}/git/ref/heads/master", api=True))
        commit = ref["object"]["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("expected a full upstream commit SHA")
    if commit == old_report["upstream_commit"]:
        print("Pinned upstream commit unchanged; all local snapshots verified")
        return
    remote = metadata(cfg, commit)
    lock = {"schema_version": 2, "repository": UPSTREAM, "commit": commit, "files": {}}
    report = ["## Native upstream candidate", "", f"Source: https://github.com/{UPSTREAM}/commit/{commit}", "",
              "All file bytes, comments, ordering, duplicates and native rule types are preserved. Extensions remain disabled.", "",
              "| Native file | Added entries | Removed entries |", "| --- | ---: | ---: |"]
    with tempfile.TemporaryDirectory(dir=root.parent) as tmp:
        stage = Path(tmp)
        for name in ("sources.json", "routing.json"):
            shutil.copy(root / name, stage / name)
        def download(source):
            path = source["path"]
            data = fetch(f"https://raw.githubusercontent.com/{UPSTREAM}/{commit}/{path}")
            added, removed = validate_download(source, data, remote[path], old_contents[path], cfg["max_change_ratio"])
            p = snapshot_path(stage, path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            return path, added, removed
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(download, cfg["files"]))
        for path, added, removed in results:
            lock["files"][path] = {"git_blob_sha": remote[path]["sha"], "size": remote[path]["size"]}
            if added or removed:
                report.append(f"| {path} | {added} | {removed} |")
        (stage / "upstream/lock.json").write_text(dump(lock))
        build(root=stage)
        build(check=True, root=stage)
        # A failed download, hash check or complete staged build leaves tracked files untouched.
        for folder in ("upstream", "dist"):
            target = root / folder
            expected = {p.relative_to(stage / folder) for p in (stage / folder).rglob("*") if p.is_file()}
            for p in target.rglob("*"):
                if p.is_file() and p.relative_to(target) not in expected:
                    p.unlink()
            for path in expected:
                p = target / path
                p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(stage / folder / path, p)
    report.extend(["", "Candidate only. Review upstream changes and client adapters before manually publishing stable.",
                   "No filtering, deduplication, cross-client conversion or custom rules were applied."])
    (root / ".update-report.md").write_text("\n".join(report) + "\n")
    print(f"Verified native candidate: {commit}; stable unchanged")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", help="optional full upstream commit SHA; otherwise fetch master once")
    args = parser.parse_args()
    main(args.commit)
