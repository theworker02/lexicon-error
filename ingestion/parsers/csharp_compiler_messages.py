#!/usr/bin/env python3
"""Turn a saved Microsoft compiler-message index into a reviewable JSON queue."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Text or HTML snapshot from learn.microsoft.com")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    codes = sorted(set(re.findall(r"\bCS\d{4}\b", args.source.read_text(encoding="utf-8"))))
    entries = [{"id": f"cs_{code.lower()}", "language": "C#", "code": code,
      "category": "Unclassified", "severity": "Compiler Error", "title": "Needs editorial enrichment",
      "description": "Imported from Microsoft's compiler-message index; add a reviewed explanation.",
      "bad_example": "// Add a minimal reproduction.", "good_example": "// Add the corresponding repair.",
      "version_introduced": None, "version_deprecated": None,
      "source_url": f"https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/compiler-messages/{code.lower()}"} for code in codes]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(entries)} C# compiler-message stubs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
