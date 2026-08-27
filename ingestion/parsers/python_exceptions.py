#!/usr/bin/env python3
"""Generate structured Python built-in exception entries from a local interpreter."""
from __future__ import annotations

import argparse
import builtins
import inspect
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    items = []
    for name, value in inspect.getmembers(builtins, inspect.isclass):
        if name.startswith("_"):
            continue
        if not issubclass(value, BaseException) or value is BaseException:
            continue
        title = (value.__doc__ or name).split("\n", 1)[0].strip()
        items.append({"id": f"py_{name.lower()}", "language": "Python", "code": name,
          "category": "Runtime", "severity": "Runtime Exception", "title": title,
          "description": value.__doc__ or f"Python built-in exception {name}.",
          "bad_example": "# Add a minimal reproduction.", "good_example": "# Add a reviewed repair.",
          "version_introduced": "1.0", "version_deprecated": None,
          "source_url": f"https://docs.python.org/3/library/exceptions.html#{name}"})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(items, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(items)} Python exception stubs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
