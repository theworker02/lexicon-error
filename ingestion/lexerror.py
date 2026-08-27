#!/usr/bin/env python3
"""Local Lexicon Error maintenance CLI. No command sends diagnostic data over the network."""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

from coverage import coverage, validate_coverage
from knowledge import DATASET_VERSION, detect, statistics, validate_knowledge


def connect(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise ValueError(f"Database not found: {path}")
    return sqlite3.connect(path)


def coverage_command(connection: sqlite3.Connection, as_json: bool) -> int:
    records = coverage(connection)
    if as_json:
        print(json.dumps(records, indent=2))
        return 0
    print(f"{'Language':<18}{'Records':>9}{'Target':>10}{'Progress':>11}  Tier")
    for record in records:
        if not record["records"]:
            continue
        print(f"{record['language']:<18}{record['records']:>9}{record['target']:>10}{record['progress']:>10.1f}%  {record['tier']}")
    return 0


def validate_command(connection: sqlite3.Connection) -> int:
    failures = [*validate_knowledge(connection), *validate_coverage(connection)]
    if failures:
        print("Validation failed:\n- " + "\n- ".join(failures), file=sys.stderr)
        return 1
    print("Knowledge graph and coverage rules are valid.")
    return 0


def release_manifest(connection: sqlite3.Connection, destination: Path) -> int:
    stats = statistics(connection)
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": DATASET_VERSION,
        "schema_version": "2.0",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "records": stats["diagnostics"],
        "languages": stats["languages"],
        "tools": stats["tools"],
        "concepts": stats["concepts"],
        "verified": stats["verified"],
    }
    destination.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {destination}.")
    return 0


def export_records(connection: sqlite3.Connection, destination: Path, fmt: str) -> int:
    rows = connection.execute("""
        SELECT e.id, m.canonical_id, e.language, m.tool_id, e.code, e.category, e.severity, e.title,
          e.description, e.bad_example, e.good_example, e.version_introduced, e.version_deprecated,
          e.source_url, m.classifications, m.normalized_severity, m.fingerprint, m.provenance, m.verification_status
        FROM entries e JOIN error_metadata m ON m.entry_id=e.id ORDER BY e.language, e.code, e.id
    """).fetchall()
    columns = [column[0] for column in connection.execute("""
        SELECT e.id, m.canonical_id, e.language, m.tool_id, e.code, e.category, e.severity, e.title,
          e.description, e.bad_example, e.good_example, e.version_introduced, e.version_deprecated,
          e.source_url, m.classifications, m.normalized_severity, m.fingerprint, m.provenance, m.verification_status
        FROM entries e JOIN error_metadata m ON m.entry_id=e.id LIMIT 0
    """).description]
    destination.parent.mkdir(parents=True, exist_ok=True)
    data = [dict(zip(columns, row, strict=True)) for row in rows]
    if fmt == "json":
        destination.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    elif fmt == "jsonl":
        destination.write_text("".join(json.dumps(item) + "\n" for item in data), encoding="utf-8")
    elif fmt == "csv":
        with destination.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(data)
    else:
        raise ValueError(f"Unsupported export format: {fmt}")
    print(f"Exported {len(data)} records to {destination}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("artifacts/lexicon-error.db"))
    commands = parser.add_subparsers(dest="command", required=True)
    coverage_parser = commands.add_parser("coverage")
    coverage_parser.add_argument("--json", action="store_true")
    commands.add_parser("validate")
    detect_parser = commands.add_parser("detect")
    detect_parser.add_argument("message")
    manifest_parser = commands.add_parser("release-manifest")
    manifest_parser.add_argument("--output", type=Path, required=True)
    export_parser = commands.add_parser("export")
    export_parser.add_argument("--format", choices=("json", "jsonl", "csv"), required=True)
    export_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        with connect(args.database) as connection:
            if args.command == "coverage":
                return coverage_command(connection, args.json)
            if args.command == "validate":
                return validate_command(connection)
            if args.command == "detect":
                print(json.dumps(detect(connection, args.message), indent=2))
                return 0
            if args.command == "release-manifest":
                return release_manifest(connection, args.output)
            return export_records(connection, args.output, args.format)
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f"lexerror: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
