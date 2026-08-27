#!/usr/bin/env python3
"""Extract SQLite primary and extended result-code identifiers for SQL diagnostics."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SOURCE_URL = "https://github.com/sqlite/sqlite/blob/master/src/sqlite.h.in"
DEFINE = re.compile(r"^#define\s+(SQLITE_[A-Z0-9_]+)\s+(.+?)\s*$", re.MULTILINE)
PREFIXES = ("SQLITE_IOERR", "SQLITE_LOCKED", "SQLITE_BUSY", "SQLITE_CANTOPEN", "SQLITE_CONSTRAINT", "SQLITE_CORRUPT", "SQLITE_READONLY", "SQLITE_ABORT", "SQLITE_AUTH", "SQLITE_NOTICE", "SQLITE_WARNING")
PRIMARY = {
    "SQLITE_OK", "SQLITE_ERROR", "SQLITE_INTERNAL", "SQLITE_PERM", "SQLITE_ABORT", "SQLITE_BUSY", "SQLITE_LOCKED", "SQLITE_NOMEM",
    "SQLITE_READONLY", "SQLITE_INTERRUPT", "SQLITE_IOERR", "SQLITE_CORRUPT", "SQLITE_NOTFOUND", "SQLITE_FULL", "SQLITE_CANTOPEN",
    "SQLITE_PROTOCOL", "SQLITE_EMPTY", "SQLITE_SCHEMA", "SQLITE_TOOBIG", "SQLITE_CONSTRAINT", "SQLITE_MISMATCH", "SQLITE_MISUSE",
    "SQLITE_NOLFS", "SQLITE_AUTH", "SQLITE_FORMAT", "SQLITE_RANGE", "SQLITE_NOTADB", "SQLITE_NOTICE", "SQLITE_WARNING",
}


def category(code: str) -> str:
    if any(token in code for token in ("BUSY", "LOCKED", "PROTOCOL")):
        return "Concurrency"
    if any(token in code for token in ("IOERR", "CANTOPEN", "FULL", "READONLY")):
        return "IO"
    if any(token in code for token in ("NOMEM", "TOOBIG")):
        return "Memory"
    if any(token in code for token in ("AUTH", "PERM")):
        return "Security"
    return "Database"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    entries: list[dict[str, object]] = []
    for code, expression in DEFINE.findall(args.source.read_text(encoding="utf-8")):
        if code not in PRIMARY and not code.startswith(PREFIXES):
            continue
        display = code.removeprefix("SQLITE_").replace("_", " ").title()
        entries.append({
            "id": f"sql_{code.lower()}",
            "language": "SQL",
            "code": code,
            "category": category(code),
            "severity": "Runtime Exception",
            "title": display,
            "description": f"SQLite result code {code} ({expression}) from the public SQLite API. It represents a database-engine outcome surfaced while executing SQL; a precise trigger and repair are pending editorial review.",
            "bad_example": "-- Registry-only record; a minimal reproduction is pending editorial review.",
            "good_example": "-- Registry-only record; a source-backed repair is pending editorial review.",
            "version_introduced": None,
            "version_deprecated": None,
            "source_url": SOURCE_URL,
            "tier": 3,
            "frequency": "Uncommon",
            "situational_context": ["SQLite database engine", "SQL execution"],
            "interaction_types": ["runtime"],
            "related_errors": [],
        })
    entries = list({entry["id"]: entry for entry in entries}.values())
    entries.sort(key=lambda entry: str(entry["code"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(entries)} SQLite result-code records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
