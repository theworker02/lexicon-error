#!/usr/bin/env python3
"""Extract V8 user-facing message templates into a JavaScript review queue."""
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

SOURCE_URL = "https://github.com/v8/v8/blob/main/src/common/message-template.h"
TEMPLATE = re.compile(r"T\(\s*([A-Za-z0-9]+)\s*,\s*((?:\"(?:[^\"\\]|\\.)*\"\s*)+)\)\\?", re.DOTALL)
SECTION = re.compile(r"/\*\s*([A-Za-z][A-Za-z0-9 ]*?)\s*\*/")


def text_from_literals(value: str) -> str:
    return "".join(ast.literal_eval(part) for part in re.findall(r'"(?:[^"\\]|\\.)*"', value))


def identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def severity(section: str) -> str:
    return "Compiler Error" if section == "SyntaxError" else "Runtime Exception"


def category(section: str) -> str:
    if section == "SyntaxError":
        return "Syntax"
    if section in {"TypeError", "RangeError"}:
        return "Type System"
    if section == "ReferenceError":
        return "Modules"
    return "Runtime"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.read_text(encoding="utf-8")
    sections = [(match.start(), match.group(1).replace(" ", "")) for match in SECTION.finditer(source)]
    entries: list[dict[str, object]] = []
    for match in TEMPLATE.finditer(source):
        name = match.group(1)
        message = text_from_literals(match.group(2)).replace("%", "{value}").strip()
        if not message or name in {"None", "PlaceholderOnly"}:
            continue
        section = next((kind for index, kind in reversed(sections) if index < match.start()), "Error")
        entries.append({
            "id": f"js_v8_{identifier(section)}_{identifier(name)}",
            "language": "JavaScript",
            "code": f"v8::{section}::{name}",
            "category": category(section),
            "severity": severity(section),
            "title": message,
            "description": f"V8 {section} message template `{name}`. This source-qualified runtime diagnostic is derived from the official V8 message registry; editorial context, reproduction, and repair are pending review.",
            "bad_example": "// Registry-only record; a minimal reproduction is pending editorial review.",
            "good_example": "// Registry-only record; a source-backed repair is pending editorial review.",
            "version_introduced": None,
            "version_deprecated": None,
            "source_url": SOURCE_URL,
            "tier": 3,
            "frequency": "Uncommon",
            "situational_context": ["V8 JavaScript runtime"],
            "interaction_types": ["runtime"],
            "related_errors": []
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(entries)} V8 message templates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
