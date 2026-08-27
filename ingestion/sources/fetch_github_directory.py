#!/usr/bin/env python3
"""Recursively snapshot a public GitHub contents directory using the Contents API."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

USER_AGENT = "LexiconError ingestion/0.1 (offline diagnostic indexer)"


def fetch(url: str) -> object:
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}), timeout=30) as response:
        return json.loads(response.read())


def walk(url: str) -> list[dict[str, object]]:
    listing = fetch(url)
    if not isinstance(listing, list):
        raise ValueError(f"Expected a GitHub directory listing at {url}")
    files: list[dict[str, object]] = []
    for item in listing:
        if item.get("type") == "file":
            files.append(item)
        elif item.get("type") == "dir":
            files.extend(walk(str(item["url"])))
    return files


def download(url: str) -> bytes:
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=30) as response:
        return response.read()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("api_url")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--suffix", default=".md")
    parser.add_argument("--upstream-ref", required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    locked: list[dict[str, object]] = []
    for item in walk(args.api_url):
        path = str(item["path"])
        if not path.endswith(args.suffix):
            continue
        relative = Path(path).name if "/" not in path else Path(*path.split("/")[-5:])
        destination = args.output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        body = download(str(item["download_url"]))
        destination.write_bytes(body)
        locked.append({"snapshot": str(destination).replace("\\", "/"), "source": item["html_url"], "upstream_ref": args.upstream_ref, "retrieved_at": datetime.now(UTC).replace(microsecond=0).isoformat(), "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()})
    prior = json.loads(args.lock.read_text(encoding="utf-8")) if args.lock.exists() else []
    prefix = str(args.output).replace("\\", "/")
    args.lock.parent.mkdir(parents=True, exist_ok=True)
    args.lock.write_text(json.dumps([*(item for item in prior if not str(item.get("snapshot", "")).startswith(prefix)), *locked], indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(locked)} files to {args.output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
