#!/usr/bin/env python3
"""Validate LexiconError JSON entries against the canonical JSON Schema."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_entries(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else [payload]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--schema", type=Path, default=Path(__file__).parents[1] / "data" / "error-entry.schema.json")
    args = parser.parse_args()
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError:
        print("Missing optional dependency: pip install -r ingestion/requirements.txt", file=sys.stderr)
        return 2
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    failures = 0
    for file in args.files:
        for index, entry in enumerate(load_entries(file)):
            errors = sorted(validator.iter_errors(entry), key=lambda error: list(error.path))
            for error in errors:
                location = ".".join(str(segment) for segment in error.path) or "entry"
                print(f"{file}:{index}:{location}: {error.message}", file=sys.stderr)
                failures += 1
    if failures:
        return 1
    print(f"Validated {sum(len(load_entries(file)) for file in args.files)} entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
