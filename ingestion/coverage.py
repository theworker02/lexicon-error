"""Truthful, database-derived Lexicon Error coverage metrics and quality gates."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
VERIFIED_STATUSES = {"Official", "Verified", "Community Verified"}


def load_targets() -> dict[str, int]:
    records = json.loads((ROOT / "data" / "knowledge" / "coverage-targets.json").read_text(encoding="utf-8"))
    return {record["language_id"]: int(record["target"]) for record in records}


def percentage(numerator: int, denominator: int) -> float:
    return round((100 * numerator / denominator), 1) if denominator else 0.0


def tier(metrics: dict[str, Any]) -> str:
    if not metrics["records"]:
        return "Experimental"
    quality = metrics["quality"]
    if metrics["records"] >= metrics["target"] > 0 and all(quality[field] >= minimum for field, minimum in {"verified": 95, "explanations": 95, "examples": 60, "fixes": 70, "sources": 95}.items()):
        return "Comprehensive"
    if metrics["target"] and metrics["records"] >= metrics["target"] * 0.5 and all(quality[field] >= minimum for field, minimum in {"verified": 70, "explanations": 70, "sources": 95}.items()):
        return "Broad"
    if metrics["records"] >= 50 and quality["sources"] >= 95:
        return "Developing"
    return "Experimental"


def coverage(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    targets = load_targets()
    rows = connection.execute("""
        SELECT l.id, l.name, COUNT(DISTINCT e.id),
          COUNT(DISTINCT CASE WHEN m.verification_status IN ('Official', 'Verified', 'Community Verified') THEN e.id END),
          COUNT(DISTINCT CASE WHEN e.description NOT LIKE '%pending editorial review%' AND e.title <> 'Needs editorial enrichment' THEN e.id END),
          COUNT(DISTINCT CASE WHEN e.bad_example NOT LIKE '%pending editorial review%' AND e.bad_example NOT LIKE '%Add a minimal reproduction%' THEN e.id END),
          COUNT(DISTINCT CASE WHEN e.good_example NOT LIKE '%pending editorial review%' AND e.good_example NOT LIKE '%Add a reviewed repair%' THEN e.id END),
          COUNT(DISTINCT CASE WHEN e.source_url IS NOT NULL THEN e.id END),
          COUNT(DISTINCT CASE WHEN e.version_introduced IS NOT NULL OR e.version_deprecated IS NOT NULL THEN e.id END),
          COUNT(DISTINCT CASE WHEN r.source_entry_id IS NOT NULL THEN e.id END),
          COUNT(DISTINCT m.tool_id)
        FROM languages l
        LEFT JOIN error_metadata m ON m.language_id = l.id
        LEFT JOIN entries e ON e.id = m.entry_id
        LEFT JOIN error_relationships r ON r.source_entry_id = e.id
        GROUP BY l.id, l.name
        ORDER BY l.name
    """).fetchall()
    records: list[dict[str, Any]] = []
    for row in rows:
        language_id, name, total, verified, explained, examples, fixes, sources, versions, relationships, tools = (int(value or 0) if index >= 2 else value for index, value in enumerate(row))
        item: dict[str, Any] = {
            "language_id": language_id,
            "language": name,
            "records": total,
            "target": targets.get(language_id, 0),
            "progress": percentage(total, targets.get(language_id, 0)),
            "tools": tools,
            "quality": {
                "verified": percentage(verified, total),
                "explanations": percentage(explained, total),
                "examples": percentage(examples, total),
                "fixes": percentage(fixes, total),
                "sources": percentage(sources, total),
                "versions": percentage(versions, total),
                "relationships": percentage(relationships, total),
            },
        }
        item["tier"] = tier(item)
        records.append(item)
    return records


def validate_coverage(connection: sqlite3.Connection) -> list[str]:
    failures: list[str] = []
    for record in coverage(connection):
        if record["tier"] == "Comprehensive":
            quality = record["quality"]
            for field, minimum in {"verified": 95, "explanations": 95, "examples": 60, "fixes": 70, "sources": 95}.items():
                if quality[field] < minimum:
                    failures.append(f"{record['language']} is marked Comprehensive without {field} >= {minimum}%")
    return failures
