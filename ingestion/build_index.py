#!/usr/bin/env python3
"""Build a portable LexiconError SQLite/FTS5 database from JSON entry files.

Example: python ingestion/build_index.py data/seed.json --output artifacts/lexicon-error.db
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from coverage import validate_coverage
from knowledge import populate_knowledge, validate_knowledge

REQUIRED = {"id", "language", "code", "category", "severity", "title", "description", "bad_example", "good_example"}
OPTIONAL = {"version_introduced", "version_deprecated", "source_url", "source_reference", "tier", "frequency", "situational_context", "interaction_types", "related_errors", "state_snapshot"}
SEVERITIES = {"Compiler Error", "Warning", "Runtime Exception", "Linter Rule", "Fatal", "Undefined Behavior"}
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)+$")

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
CREATE TABLE entries (
  id TEXT PRIMARY KEY NOT NULL, language TEXT NOT NULL, code TEXT NOT NULL,
  category TEXT NOT NULL, severity TEXT NOT NULL, title TEXT NOT NULL,
  description TEXT NOT NULL, bad_example TEXT NOT NULL, good_example TEXT NOT NULL,
  version_introduced TEXT, version_deprecated TEXT, source_url TEXT,
  tier INTEGER NOT NULL DEFAULT 1, frequency TEXT NOT NULL DEFAULT 'Common',
  situational_context TEXT NOT NULL DEFAULT '[]', interaction_types TEXT NOT NULL DEFAULT '[]',
  related_errors TEXT NOT NULL DEFAULT '[]', state_snapshot TEXT
);
CREATE VIRTUAL TABLE entries_fts USING fts5(code, title, description, language, category,
  content='entries', content_rowid='rowid', tokenize='unicode61 remove_diacritics 2');
CREATE TRIGGER entries_ai AFTER INSERT ON entries BEGIN
 INSERT INTO entries_fts(rowid, code, title, description, language, category)
 VALUES (new.rowid, new.code, new.title, new.description, new.language, new.category);
END;
"""


def read_entries(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return payload
    raise ValueError(f"{path}: expected one object or an array of objects")


def validate(entry: dict[str, Any], origin: Path) -> None:
    extras = set(entry) - REQUIRED - OPTIONAL
    missing = REQUIRED - set(entry)
    if extras or missing:
        raise ValueError(f"{origin}: schema mismatch; missing={sorted(missing)}, extra={sorted(extras)}")
    if not ID_PATTERN.fullmatch(str(entry["id"])):
        raise ValueError(f"{origin}: invalid id {entry['id']!r}")
    if entry["severity"] not in SEVERITIES:
        raise ValueError(f"{origin}: unsupported severity {entry['severity']!r}")
    if entry.get("tier", 1) not in {1, 2, 3, 4}:
        raise ValueError(f"{origin}: tier must be 1 through 4")
    if entry.get("frequency", "Common") not in {"Common", "Uncommon", "Rare", "Situational"}:
        raise ValueError(f"{origin}: invalid frequency")
    if any(not isinstance(entry[field], str) or not entry[field].strip() for field in REQUIRED):
        raise ValueError(f"{origin}: every required value must be a non-empty string")


def canonicalize_source(entry: dict[str, Any], origin: Path) -> dict[str, Any]:
    """Accept either documented source field while persisting one canonical URL."""
    entry = dict(entry)
    source_url = entry.get("source_url")
    source_reference = entry.pop("source_reference", None)
    if source_url and source_reference and source_url != source_reference:
        raise ValueError(f"{origin}: source_url and source_reference disagree")
    if source_reference and not source_url:
        entry["source_url"] = source_reference
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", type=Path, help="JSON entry files")
    parser.add_argument("--manifest", type=Path, help="JSON file with an ordered inputs array")
    parser.add_argument("--output", required=True, type=Path, help="SQLite output path")
    parser.add_argument("--on-duplicate", choices=("error", "keep-first", "replace"), default="error", help="Policy when sources define the same id")
    args = parser.parse_args()
    inputs = list(args.inputs)
    if args.manifest:
        payload = json.loads(args.manifest.read_text(encoding="utf-8"))
        manifest_inputs = payload.get("inputs") if isinstance(payload, dict) else None
        if not isinstance(manifest_inputs, list) or not all(isinstance(item, str) for item in manifest_inputs):
            raise ValueError(f"{args.manifest}: manifest needs an ordered string inputs array")
        inputs.extend(Path(item) for item in manifest_inputs)
        if not args.inputs and isinstance(payload.get("duplicate_policy"), str):
            args.on_duplicate = payload["duplicate_policy"]
    if not inputs:
        parser.error("provide one or more inputs or --manifest")
    if args.output.exists():
        args.output.unlink()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    entries_by_id: dict[str, dict[str, Any]] = {}
    skipped = 0
    for source in inputs:
        for entry in read_entries(source):
            entry = canonicalize_source(entry, source)
            validate(entry, source)
            existing = entry["id"] in entries_by_id
            if existing and args.on_duplicate == "error":
                raise ValueError(f"Duplicate entry id {entry['id']!r}; choose an explicit --on-duplicate policy")
            if existing and args.on_duplicate == "keep-first":
                skipped += 1
                continue
            entries_by_id[entry["id"]] = entry
    entries = list(entries_by_id.values())
    with sqlite3.connect(args.output) as connection:
        connection.executescript(SCHEMA_SQL)
        connection.executemany(
            """INSERT INTO entries VALUES (:id, :language, :code, :category, :severity, :title,
            :description, :bad_example, :good_example, :version_introduced, :version_deprecated, :source_url,
            :tier, :frequency, :situational_context, :interaction_types, :related_errors, :state_snapshot)""",
            [{**{key: entry.get(key) for key in REQUIRED | OPTIONAL}, "tier": entry.get("tier", 1), "frequency": entry.get("frequency", "Common"), "situational_context": json.dumps(entry.get("situational_context", [])), "interaction_types": json.dumps(entry.get("interaction_types", [])), "related_errors": json.dumps(entry.get("related_errors", [])), "state_snapshot": json.dumps(entry["state_snapshot"]) if entry.get("state_snapshot") is not None else None} for entry in entries],
        )
        populate_knowledge(connection)
        failures = [*validate_knowledge(connection), *validate_coverage(connection)]
        if failures:
            missing_metadata = [row[0] for row in connection.execute("SELECT e.id FROM entries e LEFT JOIN error_metadata m ON m.entry_id=e.id WHERE m.entry_id IS NULL LIMIT 8")]
            detail = f"; entries without metadata={missing_metadata}" if missing_metadata else ""
            raise ValueError("Knowledge graph validation failed: " + "; ".join(failures) + detail)
        connection.execute("PRAGMA optimize")
    detail = f" ({skipped} lower-priority duplicates skipped)" if skipped else ""
    print(f"Built {args.output} with {len(entries)} entries and an FTS5 index{detail}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
