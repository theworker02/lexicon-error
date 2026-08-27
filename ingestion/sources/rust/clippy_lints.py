#!/usr/bin/env python3
"""Capture installed Clippy lint definitions without treating them as rustc lints."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

SOURCE_URL = "https://doc.rust-lang.org/clippy/lints.html"
LINT = re.compile(r"^\s+(clippy::[a-z][a-z0-9-]+)\s+(allow|warn|deny|forbid)\s+(.+)$")


def category(name: str) -> str:
    if any(part in name for part in ("unsafe", "pointer", "transmute", "ffi", "borrow")):
        return "Memory"
    if any(part in name for part in ("async", "await", "thread", "future", "lock")):
        return "Concurrency"
    if any(part in name for part in ("type", "cast", "trait", "generic", "conversion")):
        return "Type System"
    return "Lint"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--driver", default="clippy-driver")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = subprocess.check_output([args.driver, "-W", "help"], text=True, stderr=subprocess.STDOUT)
    version_output = subprocess.check_output([args.driver, "--version"], text=True, stderr=subprocess.STDOUT)
    version = next((line for line in version_output.splitlines() if line.lower().startswith("clippy")), "clippy (unknown version)")
    entries: list[dict[str, object]] = []
    for row in output.splitlines():
        match = LINT.match(row)
        if not match:
            continue
        name, default, meaning = match.groups()
        short_name = name.partition("::")[2]
        entries.append({
            "id": f"rs_clippy_{short_name.replace('-', '_')}",
            "language": "Rust",
            "code": name,
            "category": category(short_name),
            "severity": "Linter Rule",
            "title": short_name.replace("-", " "),
            "description": f"Clippy lint `{name}` ({default} by default): {meaning}. Captured from {version}; editorial examples and repair guidance are pending review.",
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
    print(f"Extracted {len(entries)} Clippy lint diagnostics from {version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
