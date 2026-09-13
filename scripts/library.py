"""Byte-exact complete rule-library snapshots, verified by Git's tree hash."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import stat


def git_object(kind, data):
    return hashlib.sha1(f"{kind} {len(data)}\0".encode() + data).hexdigest()


def scan_library(directory):
    directory = Path(directory)
    manifest = {}

    def walk(folder):
        children = []
        for path in folder.iterdir():
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise ValueError(f"unexpected non-regular library entry: {path}")
            name = os.fsencode(path.name)
            if stat.S_ISDIR(mode):
                sha = walk(path)
                children.append((name + b"/", b"40000 " + name + b"\0" + bytes.fromhex(sha)))
            else:
                data = path.read_bytes()
                sha = git_object("blob", data)
                git_mode = "100755" if mode & stat.S_IXUSR else "100644"
                relative = "rule/" + path.relative_to(directory).as_posix()
                manifest[relative] = {"git_blob_sha": sha, "size": len(data), "mode": git_mode}
                children.append((name, git_mode.encode() + b" " + name + b"\0" + bytes.fromhex(sha)))
        return git_object("tree", b"".join(value for _, value in sorted(children)))

    tree = walk(directory)
    return tree, dict(sorted(manifest.items()))


def verify_library(root, lock=None):
    root = Path(root)
    lock = lock or json.loads((root / "upstream/lock.json").read_text())
    if lock.get("schema_version") != 3 or lock.get("scope") != "complete rule/ directory":
        raise ValueError("a complete-library manifest is required")
    tree, files = scan_library(root / "upstream/blackmatrix7/rule")
    if tree != lock["rule_tree_sha"] or files != lock["files"]:
        raise ValueError("complete library differs from locked upstream tree/files")
    clients = Counter(path.split("/")[1] for path in files)
    return {"rule_tree_sha": tree, "file_count": len(files), "bytes": sum(x["size"] for x in files.values()),
            "client_files": dict(sorted(clients.items()))}
