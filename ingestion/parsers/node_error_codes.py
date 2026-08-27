#!/usr/bin/env python3
"""Extract documented Node.js ERR_* runtime error codes."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SOURCE_URL = "https://github.com/nodejs/node/blob/main/doc/api/errors.md"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    text = args.source.read_text(encoding="utf-8")
    codes = sorted(set(re.findall(r"^#{2,4}\s+`?(ERR_[A-Z0-9_]+)`?", text, flags=re.MULTILINE)))
    entries = [{"id": f"js_{code.lower()}", "language": "JavaScript", "code": code,
      "category": "Runtime", "severity": "Runtime Exception", "title": code.replace("ERR_", "").replace("_", " ").title(),
      "description": "Official Node.js runtime error code. Add a reviewed explanation and runnable repair.",
      "bad_example": "// Add a minimal reproduction.", "good_example": "// Add the corresponding repair.",
      "version_introduced": None, "version_deprecated": None, "source_url": SOURCE_URL} for code in codes]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(entries)} Node.js error codes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
