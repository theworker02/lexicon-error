#!/usr/bin/env python3
"""Small, polite downloader for official documentation snapshots.

Use this as a transport adapter; parsers never need network access during tests.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from urllib.request import Request, urlopen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    request = Request(args.url, headers={"User-Agent": "LexiconError ingestion/0.1 (offline diagnostic indexer)"})
    with urlopen(request, timeout=30) as response:
        body = response.read()
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_bytes(body)
    print(f"Saved {len(body):,} bytes to {args.destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
