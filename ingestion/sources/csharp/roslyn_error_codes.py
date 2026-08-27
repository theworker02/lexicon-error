#!/usr/bin/env python3
"""Extract active C# Roslyn ErrorCode enum members into a review queue."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SOURCE_URL = "https://github.com/dotnet/roslyn/blob/main/src/Compilers/CSharp/Portable/Errors/ErrorCode.cs"
ENTRY = re.compile(r"^\s*((?:ERR|WRN|FTL)_[A-Za-z0-9_]+)\s*=\s*(\d+)\b", re.MULTILINE)


def humanize(symbol: str) -> str:
    value = symbol.split("_", 1)[1]
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", value)
    return value.replace("_", " ")


def category(symbol: str) -> str:
    value = symbol.lower()
    if any(token in value for token in ("syntax", "parse", "token", "keyword")):
        return "Syntax"
    if any(token in value for token in ("type", "conv", "generic", "infer", "operator", "overload")):
        return "Type System"
    if any(token in value for token in ("namespace", "metadata", "assembly", "alias", "import")):
        return "Modules"
    if any(token in value for token in ("unsafe", "pointer", "fixed", "stackalloc")):
        return "Memory"
    if any(token in value for token in ("async", "await", "task", "thread")):
        return "Concurrency"
    return "Compiler"


def severity(symbol: str) -> str:
    return "Warning" if symbol.startswith("WRN_") else "Fatal" if symbol.startswith("FTL_") else "Compiler Error"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    seen: set[str] = set()
    entries: list[dict[str, object]] = []
    for symbol, value in ENTRY.findall(args.source.read_text(encoding="utf-8-sig")):
        code = f"CS{int(value):04d}"
        if code in seen:
            continue
        seen.add(code)
        entries.append({
            "id": f"cs_{code.lower()}",
            "language": "C#",
            "code": code,
            "category": category(symbol),
            "severity": severity(symbol),
            "title": humanize(symbol),
            "description": f"Roslyn's active C# ErrorCode enum declares {symbol} as {code}. This registry record preserves the authoritative diagnostic identity; editorial explanation and examples are pending review.",
            "bad_example": "// Registry-only record; a minimal reproduction is pending editorial review.",
            "good_example": "// Registry-only record; a source-backed repair is pending editorial review.",
            "version_introduced": None,
            "version_deprecated": None,
            "source_url": SOURCE_URL,
            "tier": 3,
            "frequency": "Uncommon",
            "situational_context": ["Roslyn C# compiler"],
            "interaction_types": ["compiler"],
            "related_errors": []
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(entries)} active Roslyn C# diagnostic identities.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
