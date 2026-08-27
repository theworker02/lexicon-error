#!/usr/bin/env python3
"""Create a provenance-preserving Hugging Face Dataset and Space preview package.

The package contains derived diagnostic metadata only. It intentionally excludes
raw source snapshots and contribution directories so upstream documentation and
user-local data are never republished by accident.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from coverage import coverage, validate_coverage
from knowledge import DATASET_VERSION, statistics, validate_knowledge

ROOT = Path(__file__).parents[1]
ENTRY_SCHEMA = ROOT / "data" / "error-entry.schema.json"
SOURCE_MANIFEST = ROOT / "data" / "knowledge" / "source-manifest.json"
SOURCE_LOCK = ROOT / "data" / "review" / "source-lock.json"
BRAND_ASSET = ROOT / "assets" / "branding" / "lexiconerror-mark.svg"
REQUIRED_FIELDS = {
    "id", "canonical_id", "language", "tool_id", "code", "category", "severity", "title",
    "description", "bad_example", "good_example", "version_introduced", "version_deprecated",
    "source_url", "source_reference", "tier", "frequency", "situational_context",
    "interaction_types", "related_errors", "state_snapshot", "classifications",
    "normalized_severity", "fingerprint", "provenance", "verification_status",
}


def decode(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def export_records(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """SELECT e.id, m.canonical_id, e.language, m.tool_id, e.code, e.category, e.severity, e.title,
                  e.description, e.bad_example, e.good_example, e.version_introduced, e.version_deprecated,
                  e.source_url, e.tier, e.frequency, e.situational_context, e.interaction_types,
                  e.related_errors, e.state_snapshot, m.classifications, m.normalized_severity,
                  m.fingerprint, m.provenance, m.verification_status
           FROM entries e JOIN error_metadata m ON m.entry_id = e.id
           ORDER BY e.language, e.code, e.id"""
    ).fetchall()
    records: list[dict[str, Any]] = []
    for row in rows:
        source_url = row[13]
        records.append({
            "id": row[0], "canonical_id": row[1], "language": row[2], "tool_id": row[3],
            "code": row[4], "category": row[5], "severity": row[6], "title": row[7],
            "description": row[8], "bad_example": row[9], "good_example": row[10],
            "version_introduced": row[11], "version_deprecated": row[12],
            "source_url": source_url, "source_reference": source_url, "tier": row[14],
            "frequency": row[15], "situational_context": decode(row[16], []),
            "interaction_types": decode(row[17], []), "related_errors": decode(row[18], []),
            "state_snapshot": decode(row[19], None), "classifications": decode(row[20], []),
            "normalized_severity": row[21], "fingerprint": row[22], "provenance": decode(row[23], {}),
            "verification_status": row[24],
        })
    if not records or any(set(record) != REQUIRED_FIELDS for record in records):
        raise ValueError("The database does not expose the expected Hugging Face record contract")
    return records


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dataset_card(records: int, stats: dict[str, int]) -> str:
    return f"""---
language:
- en
pretty_name: LexiconError Diagnostics
license: other
size_categories:
- 10K<n<100K
tags:
- programming-languages
- compiler-diagnostics
- runtime-exceptions
- developer-tools
- cuda
- rocm
configs:
- config_name: diagnostics
  data_files:
  - split: train
    path: data/diagnostics.jsonl
---

# LexiconError Diagnostics

![LexiconError logo](assets/lexiconerror-mark.svg)

LexiconError Diagnostics is a {records:,}-record, provenance-preserving corpus of programming-language compiler diagnostics, linter rules, runtime exceptions, infrastructure failures, and accelerator-runtime faults. It is a reference dataset, not a claim of exhaustive or fully editorially verified coverage.

## Dataset details

- Release version: `{DATASET_VERSION}`
- Records: {records:,} across {stats["languages"]} languages and {stats["tools"]} tools
- Records marked verified: {stats["verified"]:,}; generated registry records remain `Needs Review`
- Format: UTF-8 JSON Lines, one diagnostic per row
- Split: `train` is a catalog split, **not** a machine-learning train/validation recommendation

## Fields

Each row has a stable `id`, language/tool identity, code, category, severity, title, explanation, broken and corrected snippets, optional version bounds, classification/frequency/context fields, source URLs, normalized provenance, and verification state. `source_reference` mirrors the canonical `source_url` for contribution-format compatibility.

## Intended uses

- Offline developer reference, search, diagnostics grouping, evaluation fixtures, and retrieval experiments.
- Building tools that link back to official documentation.

Do not treat a `Needs Review` entry as verified remediation guidance, execute included snippets without isolation, or use this corpus as a replacement for current upstream compiler documentation.

## Provenance and licensing

This is a composite derived-metadata dataset. It deliberately excludes raw source snapshots and documentation bodies. Upstream terms vary by source; detailed license, attribution, source lock, and redistribution guidance are included in `metadata/`. The dataset is labelled `other` because no single blanket license can accurately supersede those upstream terms. See [NOTICE.md](NOTICE.md) and [LICENSE](LICENSE).

## Reproducibility

The dataset was generated from the SQLite release index with `ingestion/package_hf_dataset.py`. `metadata/release-manifest.json` records counts and SHA-256 hashes. The source snapshot lock is provided for auditability, but source snapshots themselves are intentionally omitted.
"""


def notice(sources: list[dict[str, Any]]) -> str:
    lines = ["# Third-party notices", "", "This release contains derived diagnostic metadata. Retain this notice and consult the linked source manifest before redistribution.", ""]
    for source in sources:
        lines.extend([
            f"## {source['id']}",
            f"- Source: {source['source']}",
            f"- License/terms: {source['license']}",
            f"- Attribution: {source['attribution']}",
            f"- Policy: {source['redistribution_policy']}",
            "",
        ])
    return "\n".join(lines)


def license_notice() -> str:
    return """LexiconError Diagnostics composite dataset notice

Copyright for LexiconError editorial material remains with its contributors.
The dataset also contains derived metadata from multiple upstream projects and
documentation sources. No single open-source or open-data license is granted
for the dataset as a whole. Use, redistribution, attribution, and any derivative
work must comply with the source-specific terms and notices in NOTICE.md and
metadata/source-manifest.json. Raw upstream snapshots are not part of this
release. Remove or separately review entries if your use cannot meet a source's
terms. This notice is not legal advice.
"""


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def package(database: Path, output: Path, space_sample: Path | None, pages_sample: Path | None) -> dict[str, Any]:
    if not database.is_file():
        raise ValueError(f"Database not found: {database}")
    with sqlite3.connect(database) as connection:
        failures = [*validate_knowledge(connection), *validate_coverage(connection)]
        if failures:
            raise ValueError("Release database failed validation: " + "; ".join(failures))
        records = export_records(connection)
        stats = statistics(connection)
        coverage_rows = coverage(connection)

    data_dir = output / "data"
    metadata_dir = output / "metadata"
    assets_dir = output / "assets"
    data_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    diagnostics_path = data_dir / "diagnostics.jsonl"
    write_jsonl(diagnostics_path, records)
    (data_dir / "coverage.json").write_text(json.dumps(coverage_rows, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(ENTRY_SCHEMA, metadata_dir / "error-entry.schema.json")
    shutil.copy2(SOURCE_MANIFEST, metadata_dir / "source-manifest.json")
    shutil.copy2(SOURCE_LOCK, metadata_dir / "source-lock.json")
    shutil.copy2(BRAND_ASSET, assets_dir / BRAND_ASSET.name)
    (output / "README.md").write_text(dataset_card(len(records), stats), encoding="utf-8")
    sources = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))["sources"]
    (output / "NOTICE.md").write_text(notice(sources), encoding="utf-8")
    (output / "LICENSE").write_text(license_notice(), encoding="utf-8")
    manifest = {
        "release_name": "LexiconError Diagnostics", "version": DATASET_VERSION,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "records": len(records), "languages": stats["languages"], "tools": stats["tools"],
        "verified": stats["verified"], "files": {},
        "excludes": ["raw source snapshots", "local contribution directories", "desktop application data"],
    }
    for path in (diagnostics_path, data_dir / "coverage.json", metadata_dir / "error-entry.schema.json", metadata_dir / "source-manifest.json", metadata_dir / "source-lock.json", assets_dir / BRAND_ASSET.name):
        manifest["files"][str(path.relative_to(output)).replace("\\", "/")] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    (metadata_dir / "release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if space_sample:
        space_sample.parent.mkdir(parents=True, exist_ok=True)
        space_sample.write_text(json.dumps(records[:80], indent=2) + "\n", encoding="utf-8")
        space_assets = space_sample.parent / "assets"
        space_assets.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BRAND_ASSET, space_assets / BRAND_ASSET.name)
    if pages_sample:
        pages_sample.parent.mkdir(parents=True, exist_ok=True)
        pages_sample.write_text(json.dumps(records[:80], indent=2) + "\n", encoding="utf-8")
        pages_assets = pages_sample.parent / "assets"
        pages_assets.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BRAND_ASSET, pages_assets / BRAND_ASSET.name)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "artifacts" / "lexicon-error-2026.08-reviewed.db")
    parser.add_argument("--output", type=Path, default=ROOT / "hf" / "lexiconerror-diagnostics")
    parser.add_argument("--space-sample", type=Path, default=ROOT / "hf" / "lexiconerror-space" / "sample-data.json")
    parser.add_argument("--pages-sample", type=Path, default=ROOT / "site" / "sample-data.json")
    args = parser.parse_args()
    manifest = package(args.database, args.output, args.space_sample, args.pages_sample)
    print(f"Packaged {manifest['records']:,} records in {args.output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
