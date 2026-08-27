#!/usr/bin/env python3
"""Extract Rust error-code headings from a downloaded official error index.

The output is deliberately a review queue: enrich each entry with real broken and
fixed examples before validating and importing it into LexiconError.
"""
from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="HTML saved from doc.rust-lang.org/error_codes/error-index.html")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reader = TextExtractor(); reader.feed(args.source.read_text(encoding="utf-8"))
    text = " ".join(" ".join(reader.parts).split())
    codes = sorted(set(re.findall(r"\bE\d{4}\b", text)))
    result = [{"id": f"rs_{code.lower()}", "language": "Rust", "code": code,
      "category": "Unclassified", "severity": "Compiler Error", "title": "Needs editorial enrichment",
      "description": "Imported from Rust's official error index; add a reviewed explanation.",
      "bad_example": "// Add a minimal reproduction.", "good_example": "// Add the corresponding repair.",
      "version_introduced": None, "version_deprecated": None,
      "source_url": f"https://doc.rust-lang.org/error_codes/{code}.html"} for code in codes]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(result)} Rust error-code stubs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
