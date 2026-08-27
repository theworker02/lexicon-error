#!/usr/bin/env python3
"""Record reproducible metadata for an already-downloaded source snapshot."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--source", required=True)
    parser.add_argument("--label", help="Privacy-safe snapshot label; defaults to the local path")
    parser.add_argument("--include", default="*.py", help="Glob used when fingerprinting a directory")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--upstream-ref", required=True)
    args = parser.parse_args()
    if args.snapshot.is_dir():
        digest = hashlib.sha256()
        size = 0
        ignored = {"__pycache__", "site-packages", "test", "tests"}
        for child in sorted(path for path in args.snapshot.rglob(args.include) if path.is_file() and not any(part in ignored for part in path.relative_to(args.snapshot).parts)):
            body = child.read_bytes()
            digest.update(str(child.relative_to(args.snapshot)).replace("\\", "/").encode("utf-8"))
            digest.update(body)
            size += len(body)
        sha256 = digest.hexdigest()
    else:
        body = args.snapshot.read_bytes()
        size = len(body)
        sha256 = hashlib.sha256(body).hexdigest()
    record = {
        "source": args.source,
        "upstream_ref": args.upstream_ref,
        "retrieved_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "bytes": size,
        "sha256": sha256,
        "snapshot": args.label or str(args.snapshot).replace("\\", "/"),
    }
    existing = json.loads(args.output.read_text(encoding="utf-8")) if args.output.exists() else []
    existing = [item for item in existing if item["snapshot"] != record["snapshot"]]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps([*existing, record], indent=2) + "\n", encoding="utf-8")
    print(f"Locked {args.snapshot} ({record['sha256'][:12]}...).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
