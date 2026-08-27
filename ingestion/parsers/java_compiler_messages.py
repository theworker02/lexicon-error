#!/usr/bin/env python3
"""Extract official javac compiler messages from OpenJDK's properties registry."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SOURCE_URL = "https://github.com/openjdk/jdk/blob/master/src/jdk.compiler/share/classes/com/sun/tools/javac/resources/compiler.properties"


def unfolded_lines(source: str) -> list[str]:
    lines: list[str] = []
    pending = ""
    for raw in source.splitlines():
        if raw.endswith("\\"):
            pending += raw[:-1]
            continue
        lines.append(pending + raw)
        pending = ""
    return lines


def title(key: str) -> str:
    return key.replace(".", " ").replace("_", " ").capitalize()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    entries = []
    for line in unfolded_lines(args.source.read_text(encoding="utf-8")):
        if not line.startswith(("compiler.err.", "compiler.warn.")) or "=" not in line:
            continue
        key, message = line.split("=", 1)
        severity = "Compiler Error" if key.startswith("compiler.err.") else "Warning"
        slug = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
        entries.append({"id": f"java_{slug}", "language": "Java", "code": key,
          "category": "Compiler", "severity": severity, "title": title(key.removeprefix("compiler.err.").removeprefix("compiler.warn.")),
          "description": f"Official javac diagnostic template: {message}",
          "bad_example": "// Add a minimal reproduction.", "good_example": "// Add the corresponding repair.",
          "version_introduced": None, "version_deprecated": None, "source_url": SOURCE_URL})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(entries)} javac diagnostics.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
