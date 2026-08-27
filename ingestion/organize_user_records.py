#!/usr/bin/env python3
"""Organize user-supplied Lexicon Error JSON files without overwriting their originals.

This importer is deliberately conservative: it treats numeric scenario variants as
one candidate unless their normalized language/code identity differs, preserves a
full disposition report, and only emits source-attributed records for inclusion in
the offline index. Source-less material stays in staging for editorial review.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).parents[1]
DEFAULT_INPUTS = [
    ROOT / "lexicon_master_database.json",
    ROOT / "master_lexicon_seed.json",
    ROOT / "lexicon_expanded_ecosystems.json",
    ROOT / "lexicon_tier3_ecosystems.json",
    ROOT / "lexicon_gpu_ecosystems.json",
]
LANGUAGE_ALIASES = {"C#/.NET": "C#", "Cpp": "C++", "Dart/Flutter": "Dart", "Vue.js": "JavaScript", "Bash": "Shell / Bash", "ROCm/HIP": "ROCm / HIP"}
SEVERITY_ALIASES = {
    "Runtime": "Runtime Exception", "Runtime Exception": "Runtime Exception", "CLR Runtime Exception": "Runtime Exception", "JVM Exception": "Runtime Exception",
    "Argument Fault": "Runtime Exception", "Exhaustiveness": "Runtime Exception", "Linker/Runtime": "Runtime Exception", "Type System": "Runtime Exception",
    "Name Resolution": "Runtime Exception", "Parameter Fault": "Runtime Exception", "Class Mismatch": "Runtime Exception", "System Dependency": "Runtime Exception",
    "Lookup Fault": "Runtime Exception", "HTTP Fault": "Runtime Exception", "Connection Failure": "Runtime Exception", "Container Fault": "Runtime Exception",
    "Protocol Fault": "Runtime Exception", "Runtime Panic": "Runtime Exception", "Runtime Boundary Fault": "Runtime Exception", "Reference Fault": "Runtime Exception",
    "Decoding Fault": "Runtime Exception", "Stack Overflow": "Runtime Exception", "Initialization Fault": "Runtime Exception",
    "Compiler Error": "Compiler Error", "Compiler Diagnostic": "Compiler Error", "Build Error": "Compiler Error", "Build Failure": "Compiler Error", "Syntax Fault": "Compiler Error",
    "Compiler Warning": "Warning", "Build Warning": "Warning", "Runtime Warning": "Warning", "Standard Diagnostic": "Linter Rule",
    "Fatal": "Fatal", "Fatal Error": "Fatal", "Fatal Exception": "Fatal", "Fatal / Panic": "Fatal", "Fatal Panic": "Fatal", "Race Condition Panic": "Fatal", "CLR Fatal": "Fatal",
    "Runtime Fatal": "Fatal", "Segmentation Fault": "Runtime Exception",
}
FORMAL_VARIANT = re.compile(r"^((?:CS|TS|E)\d{4}|SIG[A-Z]+|GO_[A-Z0-9_]+|TEMPLATE_[A-Z0-9_]+|ZIG_[A-Z0-9_]+)[_-]\d+$")
BRACKETED_REFERENCE = re.compile(r"\s*\[Reference Source:[^\]]+\]")


def language(value: str) -> str:
    return LANGUAGE_ALIASES.get(value.strip(), value.strip())


def canonical_code(value: str) -> str:
    match = FORMAL_VARIANT.match(value.strip())
    return match.group(1) if match else value.strip()


def title(description: str, code: str) -> str:
    sentence = description.split(".", 1)[0].strip()
    return sentence[:160] if sentence else code


def context(value: object) -> list[str]:
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if isinstance(value, str) and value.strip() and "variant" not in value.lower() and "thread context" not in value.lower():
        return [value.strip()]
    return []


def interaction(category: str) -> list[str]:
    value = category.lower()
    if any(token in value for token in ("concurrency", "thread", "async")):
        return ["concurrency"]
    if any(token in value for token in ("parser", "syntax")):
        return ["parser"]
    if any(token in value for token in ("compiler", "build", "compilation")):
        return ["compiler"]
    return ["runtime"]


def is_authoritative_source(value: object) -> bool:
    """A search-result URL is a lead, not provenance for an includable record."""
    if not isinstance(value, str) or not value.startswith(("https://", "http://")):
        return False
    host = urlparse(value).hostname or ""
    return host not in {"google.com", "www.google.com", "bing.com", "www.bing.com"}


def source_url(value: object, language_name: str) -> str | None:
    if not isinstance(value, str):
        return None
    # User GPU records intentionally cite both vendor documentation roots in one
    # display string. Store the authoritative vendor root for the record instead.
    if " or " in value:
        options = [item.strip() for item in value.split(" or ")]
        if language_name == "CUDA":
            return next((item for item in options if "nvidia" in item.lower()), None)
        if language_name == "ROCm / HIP":
            return next((item for item in options if "amd" in item.lower() or "rocm" in item.lower()), None)
    return value if value.startswith(("https://", "http://")) else None


def normalized(entry: dict[str, Any]) -> dict[str, Any]:
    raw_description = str(entry.get("description", "")).strip()
    description = BRACKETED_REFERENCE.sub("", raw_description).strip()
    code = canonical_code(str(entry.get("code", "")))
    language_name = language(str(entry.get("language", "")))
    source = source_url(entry.get("source_url") or entry.get("source_reference"), language_name)
    return {
        "id": re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", str(entry.get("id", "")).lower())).strip("_"),
        "language": language_name,
        "code": code,
        "category": str(entry.get("category", "Unclassified")).strip() or "Unclassified",
        "severity": SEVERITY_ALIASES.get(str(entry.get("severity", "")).strip(), "Runtime Exception"),
        "title": title(description, code),
        "description": description or f"User-submitted diagnostic candidate for {code}; editorial explanation is pending review.",
        # Preserve original snippets in the supplied root files. Candidate snippets are not
        # promoted until an editor validates that they reproduce this exact diagnostic.
        "bad_example": "// Registry-only record; a minimal reproduction is pending editorial review.",
        "good_example": "// Registry-only record; a source-backed repair is pending editorial review.",
        "version_introduced": entry.get("version_introduced") or None,
        "version_deprecated": entry.get("version_deprecated") or None,
        "source_url": source,
        "tier": 3,
        "frequency": "Situational",
        "situational_context": context(entry.get("situational_context")),
        "interaction_types": interaction(str(entry.get("category", ""))),
        "related_errors": [],
    }


def existing_identities() -> set[tuple[str, str]]:
    identities: set[tuple[str, str]] = set()
    for source in [ROOT / "data" / "seed.json", *(ROOT / "data" / "review").glob("*.json")]:
        if source.name.startswith("user-"):
            continue
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for entry in payload if isinstance(payload, list) else [payload]:
            if isinstance(entry, dict) and entry.get("language") and entry.get("code"):
                identities.add((language(str(entry["language"])), canonical_code(str(entry["code"]))))
    return identities


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--review-output", type=Path, default=ROOT / "data" / "review" / "user-attributed-candidates.json")
    parser.add_argument("--staging-output", type=Path, default=ROOT / "data" / "review" / "user-unattributed-staging.json")
    parser.add_argument("--report", type=Path, default=ROOT / "data" / "review" / "user-import-report.json")
    args = parser.parse_args()
    grouped: dict[tuple[str, str], list[tuple[Path, dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    received = 0
    for source in args.inputs:
        payload = json.loads(source.read_text(encoding="utf-8"))
        for raw in payload if isinstance(payload, list) else [payload]:
            if not isinstance(raw, dict):
                continue
            received += 1
            candidate = normalized(raw)
            grouped[(candidate["language"], candidate["code"])].append((source, raw, candidate))
    existing = existing_identities()
    attributed: list[dict[str, Any]] = []
    unattributed: list[dict[str, Any]] = []
    report_entries: list[dict[str, Any]] = []
    for identity, variants in sorted(grouped.items()):
        preferred = next((candidate for _, _, candidate in variants if candidate["source_url"]), variants[0][2])
        original_ids = [str(raw.get("id", "")) for _, raw, _ in variants]
        if identity in existing:
            disposition = "existing-canonical-diagnostic"
        elif is_authoritative_source(preferred["source_url"]):
            disposition = "source-attributed-needs-review"
            attributed.append(preferred)
        else:
            disposition = "missing-source-needs-review"
            unattributed.append(preferred)
        report_entries.append({"language": identity[0], "code": identity[1], "canonical_candidate_id": preferred["id"], "source_files": sorted({str(source.relative_to(ROOT)).replace("\\", "/") for source, _, _ in variants}), "source_variant_ids": original_ids, "variant_count": len(variants), "disposition": disposition, "source_url": preferred["source_url"]})
    for output, records in [(args.review_output, attributed), (args.staging_output, unattributed)]:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    report = {"received_records": received, "unique_language_code_candidates": len(grouped), "source_attributed_candidates": len(attributed), "unattributed_staging_candidates": len(unattributed), "existing_canonical_collisions": sum(1 for item in report_entries if item["disposition"] == "existing-canonical-diagnostic"), "records": report_entries}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Organized {received} supplied records into {len(grouped)} canonical candidates: {len(attributed)} attributed review candidates, {len(unattributed)} source-less staging candidates, {report['existing_canonical_collisions']} existing diagnostic collisions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
