#!/usr/bin/env python3
"""Manually copy the COMPLETE upstream rule/ tree at one fixed Git commit."""
import argparse
from collections import Counter
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import tempfile

from library import scan_library, verify_library
from rules import ROOT, UPSTREAM, build, dump, entries, git_blob, read_config, snapshot_path

URL = f"https://github.com/{UPSTREAM}.git"


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def extract_archive(archive, target):
    """Only copy ordinary files/directories below rule/; do not follow links."""
    with tarfile.open(archive, "r:") as tar:
        for member in tar:
            path = PurePosixPath(member.name)
            if path.is_absolute() or not path.parts or path.parts[0] != "rule" or ".." in path.parts:
                raise ValueError("unexpected archive path")
            dest = target.joinpath(*path.parts)
            if member.isdir():
                dest.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                dest.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as src, dest.open("wb") as out:
                    shutil.copyfileobj(src, out)
                dest.chmod(0o755 if member.mode & 0o100 else 0o644)
            else:
                raise ValueError("non-regular upstream archive entry requires review")


def acquire(commit, work, checkout=None):
    repo = Path(checkout).resolve() if checkout else work / "git-source"
    if checkout is None:
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        # Fetch the pinned commit, not a changing raw URL; no credentials are needed.
        subprocess.run(["git", "-C", str(repo), "fetch", "--depth=1", "--no-tags", URL, commit], check=True)
    if git(repo, "rev-parse", f"{commit}^{{commit}}") != commit:
        raise ValueError("source checkout does not contain the requested commit")
    expected_tree = git(repo, "rev-parse", f"{commit}:rule")
    archive = work / "rule.tar"
    subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", f"--output={archive}", commit, "rule"], check=True)
    destination = work / "candidate/upstream/blackmatrix7"
    destination.mkdir(parents=True)
    extract_archive(archive, destination)
    tree, manifest = scan_library(destination / "rule")
    if tree != expected_tree:
        raise ValueError("downloaded complete rule tree differs from upstream Git tree")
    return tree, manifest


def guard_changes(cfg, root, stage, old_lock, new_files):
    old_files = old_lock["files"]
    if old_lock.get("schema_version") == 3:
        added = set(new_files) - set(old_files)
        removed = set(old_files) - set(new_files)
        if max(len(added), len(removed)) / max(len(old_files), 1) > cfg["max_change_ratio"]:
            raise ValueError("unusually large library file-count change; existing snapshot unchanged")
    selected = {s["path"] for s in cfg["files"] if s["role"] == "base"}
    for category in cfg["categories"]:
        companion = f"rule/Shadowrocket/{category}/{category}_Domain.list"
        if companion in new_files and companion not in selected:
            raise ValueError(f"new companion domain set: {companion}; update adapter inputs")
    for item in cfg["files"]:
        path = item["path"]
        if path not in new_files:
            raise ValueError(f"adapter input removed upstream: {path}; review adapter configuration")
        if item["format"] == "markdown":
            continue
        before = Counter(entries(snapshot_path(root, path).read_bytes(), item["format"]))
        after = Counter(entries(snapshot_path(stage, path).read_bytes(), item["format"]))
        if max(sum((after - before).values()), sum((before - after).values())) / max(sum(before.values()), 1) > cfg["max_change_ratio"]:
            raise ValueError(f"{path}: unusually large entry change; existing snapshot unchanged")


def main(commit=None, root=None, checkout=None):
    root = (root or ROOT).resolve()
    cfg = read_config(root)
    old = json.loads((root / "upstream/lock.json").read_text())
    if old.get("schema_version") == 3:
        verify_library(root, old)
    else:
        # Migration from the previously selected-file snapshot: validate it first.
        for path, meta in old["files"].items():
            data = snapshot_path(root, path).read_bytes()
            if len(data) != meta["size"] or git_blob(data) != meta["git_blob_sha"]:
                raise ValueError("existing selected-file snapshot is corrupt")
    if commit is None:
        result = subprocess.check_output(["git", "ls-remote", URL, "refs/heads/master"], text=True).strip().split()
        if len(result) != 2 or result[1] != "refs/heads/master":
            raise ValueError("cannot resolve upstream master")
        commit = result[0]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("expected a full upstream commit SHA")
    if commit == old["commit"] and old.get("schema_version") == 3:
        print("Complete library already matches the pinned upstream commit")
        return
    with tempfile.TemporaryDirectory(dir=root.parent) as tmp:
        work = Path(tmp)
        tree, manifest = acquire(commit, work, checkout)
        stage = work / "candidate"
        for name in ("sources.json", "routing.json"):
            shutil.copyfile(root / name, stage / name)
        lock = {"schema_version": 3, "repository": UPSTREAM, "scope": "complete rule/ directory",
                "commit": commit, "rule_tree_sha": tree, "files": manifest}
        (stage / "upstream/lock.json").write_text(dump(lock))
        guard_changes(cfg, root, stage, old, manifest)
        files = build(root=stage)
        summary = json.loads(files["report.json"])["library"]
        # All downloads, tree equality, guards and adapter generation passed.
        # Replace each tracked directory with the complete staged directory; retain
        # rollback copies until both have been installed successfully.
        installed = []
        try:
            for name in ("upstream", "dist"):
                backup = work / f"previous-{name}"
                (root / name).rename(backup)
                installed.append((name, backup))
                (stage / name).rename(root / name)
        except BaseException:
            for name, backup in reversed(installed):
                if (root / name).exists():
                    shutil.rmtree(root / name)
                backup.rename(root / name)
            raise
    old_paths, new_paths = set(old["files"]), set(manifest)
    changed = sum(old["files"][p]["git_blob_sha"] != manifest[p]["git_blob_sha"] for p in old_paths & new_paths)
    report = ["## Complete upstream rule-library candidate", "", f"Source: https://github.com/{UPSTREAM}/commit/{commit}",
              "", f"Entire rule/ Git tree: `{tree}`", f"Files: {len(manifest)}; bytes: {summary['bytes']}",
              f"Added files: {len(new_paths-old_paths)}; removed: {len(old_paths-new_paths)}; changed: {changed}",
              "", "Every client, category, format variant and README under upstream rule/ is copied unchanged.",
              "Client adapter selections and custom drafts are separate. No scheduled update and no stable publication occurred."]
    (root / ".update-report.md").write_text("\n".join(report) + "\n")
    print(f"Verified complete library: {len(manifest)} files, tree {tree}; stable unchanged")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", help="full upstream commit SHA; default resolves master once")
    parser.add_argument("--checkout", type=Path, help="optional existing checkout containing that exact upstream commit")
    args = parser.parse_args()
    main(args.commit, checkout=args.checkout)
