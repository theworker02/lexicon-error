#!/usr/bin/env python3
"""Extract Go type-checker error codes from the official Go source registry."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SOURCE_URL = "https://github.com/golang/go/blob/master/src/internal/types/errors/codes.go"
CODE_LINE = re.compile(r"^(?P<name>[A-Z][A-Za-z0-9]+)(?:\s+Code\s*=.*)?[,]?(?:\s*//.*)?$")


def pretty(name: str) -> str:
    return re.sub(r"(?<!^)([A-Z])", r" \1", name)


def category(name: str) -> str:
    if "Import" in name or "Pkg" in name:
        return "Linker"
    if any(fragment in name for fragment in ("Cycle", "Channel", "Mutex")):
        return "Concurrency"
    if any(fragment in name for fragment in ("Bad", "Syntax", "Label", "Stmt")):
        return "Syntax"
    return "Type System"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    entries = []
    comments: list[str] = []
    for raw_line in args.source.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("//"):
            comments.append(stripped.removeprefix("//").strip())
            continue
        if not stripped:
            if comments:
                comments.append("")
            continue
        match = CODE_LINE.fullmatch(stripped)
        if not match:
            comments = []
            continue
        name = match.group("name")
        documentation = "\n".join(comments).strip()
        comments = []
        if name in {"Code", "Test"} or ("occurs" not in documentation and "indicates" not in documentation):
            continue
        identifier = re.sub(r"(?<!^)([A-Z])", r"_\1", name).lower()
        entries.append({"id": f"go_{identifier}", "language": "Go", "code": name,
          "category": category(name), "severity": "Compiler Error", "title": pretty(name),
          "description": f"Official Go type-checker code. {documentation}",
          "bad_example": "// Add a minimal reproduction.", "good_example": "// Add the corresponding repair.",
          "version_introduced": None, "version_deprecated": None, "source_url": SOURCE_URL})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(entries)} Go type-checker error codes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
