#!/usr/bin/env python3
"""Extract MDN JavaScript error-page titles without republishing documentation bodies."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SOURCE_ROOT = "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Errors"
TITLE = re.compile(r"^title:\s*[\"']?(.+?)[\"']?\s*$", re.MULTILINE)
SLUG = re.compile(r"^slug:\s*(.+?)\s*$", re.MULTILINE)


def identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def category(title: str) -> str:
    if "SyntaxError" in title:
        return "Syntax"
    if "TypeError" in title or "RangeError" in title:
        return "Type System"
    if "ReferenceError" in title:
        return "Modules"
    return "Runtime"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    entries: list[dict[str, object]] = []
    used_ids: set[str] = set()
    for source in sorted(args.source_dir.rglob("*.md")):
        content = source.read_text(encoding="utf-8")
        title_match, slug_match = TITLE.search(content), SLUG.search(content)
        if not title_match or not slug_match or slug_match.group(1).rstrip("/") == "Web/JavaScript/Reference/Errors":
            continue
        title, slug = title_match.group(1), slug_match.group(1)
        entry_id = f"js_mdn_{identifier(slug)}"
        if entry_id in used_ids:
            continue
        used_ids.add(entry_id)
        entries.append({
            "id": entry_id,
            "language": "JavaScript",
            "code": f"mdn::{slug.rsplit('/', 1)[-1]}",
            "category": category(title),
            "severity": "Compiler Error" if "SyntaxError" in title else "Runtime Exception",
            "title": title,
            "description": f"MDN documents this JavaScript error pattern under '{slug}'. This separately attributed browser-facing record preserves the diagnostic title; editorial reproduction and repair guidance are pending review.",
            "bad_example": "// Registry-only record; a minimal reproduction is pending editorial review.",
            "good_example": "// Registry-only record; a source-backed repair is pending editorial review.",
            "version_introduced": None,
            "version_deprecated": None,
            "source_url": f"{SOURCE_ROOT}/{slug.rsplit('/', 1)[-1]}",
            "tier": 3,
            "frequency": "Uncommon",
            "situational_context": ["Browser JavaScript runtime", "MDN documented error pattern"],
            "interaction_types": ["runtime"],
            "related_errors": []
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(entries)} MDN JavaScript error pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
