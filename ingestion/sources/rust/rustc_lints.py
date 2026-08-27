#!/usr/bin/env python3
"""Capture the installed rustc lint registry as source-attributed review records."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

SOURCE_URL = "https://doc.rust-lang.org/rustc/lints/index.html"
LINT = re.compile(r"^\s+([a-z][a-z0-9-]+)\s+(allow|warn|deny|forbid)\s+(.+)$")


def category(name: str) -> str:
    if any(part in name for part in ("unsafe", "pointer", "transmute", "ffi")):
        return "Memory"
    if any(part in name for part in ("async", "thread", "suspend")):
        return "Concurrency"
    if any(part in name for part in ("lifetime", "type", "trait", "generic", "cast")):
        return "Type System"
    if any(part in name for part in ("syntax", "semicolon", "attribute", "macro")):
        return "Syntax"
    return "Lint"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rustc", default="rustc")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = subprocess.check_output([args.rustc, "-W", "help"], text=True, stderr=subprocess.STDOUT)
    version_output = subprocess.check_output([args.rustc, "--version"], text=True, stderr=subprocess.STDOUT)
    version = next((line for line in version_output.splitlines() if line.startswith("rustc ")), "rustc (unknown version)")
    section = output.partition("Lint checks provided by rustc:")[2].partition("Lint groups provided by rustc:")[0]
    entries: list[dict[str, object]] = []
    for row in section.splitlines():
        match = LINT.match(row)
        if not match:
            continue
        name, default, meaning = match.groups()
        entries.append({
            "id": f"rs_lint_{name.replace('-', '_')}",
            "language": "Rust",
            "code": f"rustc::lint::{name}",
            "category": category(name),
            "severity": "Warning",
            "title": name.replace("-", " "),
            "description": f"rustc lint `{name}` ({default} by default): {meaning}. Captured from {version}; editorial examples and repair guidance are pending review.",
            "bad_example": "// Registry-only record; a minimal reproduction is pending editorial review.",
            "good_example": "// Registry-only record; a source-backed repair is pending editorial review.",
            "version_introduced": version,
            "version_deprecated": None,
            "source_url": SOURCE_URL,
            "tier": 3,
            "frequency": "Uncommon",
            "situational_context": [version],
            "interaction_types": ["linter"],
            "related_errors": []
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(entries)} rustc lint diagnostics from {version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
