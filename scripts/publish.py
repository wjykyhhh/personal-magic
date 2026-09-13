#!/usr/bin/env python3
"""Publish a checked source tree to stable without force-pushing or rewriting history."""
from datetime import datetime, timezone
import json
import os
import re
import subprocess
import urllib.error
import urllib.request

from rules import ROOT, REPO, build, dump


def api(method, path, payload=None, missing_ok=False):
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/{path}", data=data, method=method,
        headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"], "Accept": "application/vnd.github+json", "Content-Type": "application/json", "User-Agent": "personal-magic-publisher", "X-GitHub-Api-Version": "2022-11-28"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if missing_ok and exc.code == 404:
            return None
        raise RuntimeError(f"GitHub {method} {path}: HTTP {exc.code}") from None


def main():
    if os.environ.get("GITHUB_REPOSITORY") != REPO:
        raise ValueError("publisher is scoped to the configured repository")
    files = build(check=True)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    subprocess.run(["git", "merge-base", "--is-ancestor", source, "origin/main"], cwd=ROOT, check=True)
    source_tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip()
    old = api("GET", "git/ref/heads/stable", missing_ok=True)
    parent = old["object"]["sha"] if old else source
    now = datetime.now(timezone.utc)
    report = json.loads(files["report.json"])
    metadata = {"source_commit": source, "published_at": now.isoformat(), "upstream_commit": report["upstream_commit"], "rules_sha256": report["rules_sha256"], "previous_stable_commit": parent if old else None}
    tree = api("POST", "git/trees", {"base_tree": source_tree, "tree": [{"path": "PUBLISHED.json", "mode": "100644", "type": "blob", "content": dump(metadata)}]})
    commit = api("POST", "git/commits", {"message": f"Publish checked rules from {source[:12]}", "tree": tree["sha"], "parents": [parent]})
    sha = commit["sha"]
    # One ref operation makes every file in the new stable version visible together.
    if old:
        api("PATCH", "git/refs/heads/stable", {"sha": sha, "force": False})
    else:
        api("POST", "git/refs", {"ref": "refs/heads/stable", "sha": sha})
    print(f"Published stable: https://github.com/{REPO}/commit/{sha}")
    # A tag is a convenient immutable rollback address; stable itself keeps history.
    tag = f"stable-{now:%Y%m%d-%H%M%S}-{source[:8]}"
    try:
        api("POST", "git/refs", {"ref": f"refs/tags/{tag}", "sha": sha})
        print(f"Snapshot tag: {tag}")
    except RuntimeError as exc:
        print(f"Stable is published; snapshot tag was not created: {exc}")


if __name__ == "__main__":
    main()
