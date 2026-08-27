#!/usr/bin/env python3
"""Extract Clang diagnostic definitions from a Diagnostic*Kinds.td source file."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SOURCE_URL = "https://github.com/llvm/llvm-project/blob/main/clang/include/clang/Basic/DiagnosticSemaKinds.td"
PATTERN = re.compile(r"\bdef\s+(?P<name>[A-Za-z][A-Za-z0-9_]*)\s*:\s*(?P<level>Error|Warning|Remark|Note)<\s*\"(?P<message>(?:\\.|[^\"])*)\"", re.DOTALL)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    raw = args.source.read_text(encoding="utf-8")
    entries = []
    for match in PATTERN.finditer(raw):
        level = match.group("level")
        name = match.group("name")
        identifier = re.sub(r"_+", "_", name.lower()).strip("_")
        message = " ".join(match.group("message").replace("\\\"", "\"").split())
        severity = "Compiler Error" if level == "Error" else "Warning"
        entries.append({"id": f"cpp_{identifier}", "language": "C++", "code": name,
          "category": "Compiler", "severity": severity, "title": message or name,
          "description": f"Official Clang {level.lower()} diagnostic definition. Add a reviewed explanation and repair.",
          "bad_example": "// Add a minimal reproduction.", "good_example": "// Add the corresponding repair.",
          "version_introduced": None, "version_deprecated": None, "source_url": SOURCE_URL})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(entries)} Clang diagnostics.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
