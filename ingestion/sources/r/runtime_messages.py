#!/usr/bin/env python3
"""Extract static R runtime error and warning message patterns from R sources."""
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

SOURCE_URL = "https://svn.r-project.org/R/trunk/src/main/errors.c"
CALL = re.compile(r"\b(?P<kind>error|warning)[a-zA-Z_]*\s*\([^;]{0,180}?_\(\s*(?P<literal>\"(?:[^\"\\]|\\.)*\")", re.DOTALL)


def identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    entries: list[dict[str, object]] = []
    seen: set[str] = set()
    for match in CALL.finditer(args.source.read_text(encoding="utf-8")):
        message = ast.literal_eval(match.group("literal"))
        message = re.sub(r"\s+", " ", message).strip()
        if len(message) < 6 or message in seen:
            continue
        seen.add(message)
        digest = __import__("hashlib").sha1(message.encode("utf-8")).hexdigest()[:10]
        kind = match.group("kind")
        entries.append({
            "id": f"r_{kind}_{digest}",
            "language": "R",
            "code": f"r::{kind}::{digest}",
            "category": "Runtime",
            "severity": "Warning" if kind == "warning" else "Runtime Exception",
            "title": message[:360],
            "description": f"Static R {kind} message pattern declared in the R runtime source. It is a source-qualified signature, not a standalone exception class; explanation, reproduction, and repair are pending editorial review.",
            "bad_example": "# Registry-only record; a minimal reproduction is pending editorial review.",
            "good_example": "# Registry-only record; a source-backed repair is pending editorial review.",
            "version_introduced": None,
            "version_deprecated": None,
            "source_url": SOURCE_URL,
            "tier": 3,
            "frequency": "Uncommon",
            "situational_context": ["R runtime"],
            "interaction_types": ["runtime"],
            "related_errors": [],
        })
    entries.sort(key=lambda entry: str(entry["code"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(entries)} R runtime message patterns.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
