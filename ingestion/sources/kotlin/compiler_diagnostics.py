#!/usr/bin/env python3
"""Extract named Kotlin K1 compiler diagnostics from JetBrains' registry."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SOURCE_URL = "https://github.com/JetBrains/kotlin/blob/master/compiler/frontend/src/org/jetbrains/kotlin/diagnostics/Errors.java"
FACTORY = re.compile(
    r"(?:DiagnosticFactory|DiagnosticFactoryForDeprecation)\w*[^;]{0,900}?\b(?P<name>[A-Z][A-Z0-9_]+)\s*=\s*[^;]{0,900}?\.create\(\s*(?P<severity>ERROR|WARNING)",
    re.DOTALL,
)


def title(name: str) -> str:
    return name.replace("_", " ").title()


def category(name: str) -> str:
    if any(token in name for token in ("TYPE", "CAST", "INFERENCE", "NULL", "ARGUMENT")):
        return "Type System"
    if any(token in name for token in ("SYNTAX", "PARSER", "UNEXPECTED_TOKEN")):
        return "Syntax"
    if any(token in name for token in ("COROUTINE", "SUSPEND")):
        return "Concurrency"
    return "Compiler"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    entries: list[dict[str, object]] = []
    seen: set[str] = set()
    for match in FACTORY.finditer(args.source.read_text(encoding="utf-8")):
        name = match.group("name")
        if name in seen:
            continue
        seen.add(name)
        severity = "Warning" if match.group("severity") == "WARNING" else "Compiler Error"
        entries.append({
            "id": f"kt_{name.lower()}",
            "language": "Kotlin",
            "code": f"kotlin::{name}",
            "category": category(name),
            "severity": severity,
            "title": title(name),
            "description": f"Named Kotlin compiler diagnostic `{name}` declared by JetBrains' K1 diagnostic registry. Its emitted wording depends on compiler context; curated explanation, trigger, and remediation are pending editorial review.",
            "bad_example": "// Registry-only record; a minimal reproduction is pending editorial review.",
            "good_example": "// Registry-only record; a source-backed repair is pending editorial review.",
            "version_introduced": None,
            "version_deprecated": None,
            "source_url": SOURCE_URL,
            "tier": 3,
            "frequency": "Uncommon",
            "situational_context": ["Kotlin compiler", "K1 diagnostic registry"],
            "interaction_types": ["compiler"],
            "related_errors": [],
        })
    entries.sort(key=lambda entry: str(entry["code"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(entries)} Kotlin compiler diagnostics.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
