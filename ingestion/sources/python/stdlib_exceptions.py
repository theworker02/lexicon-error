#!/usr/bin/env python3
"""Extract CPython standard-library exception classes from a local CPython Lib tree."""
from __future__ import annotations

import argparse
import ast
import json
import sys
import sysconfig
from pathlib import Path

SOURCE_ROOT = "https://github.com/python/cpython/blob/main/Lib"
BASE_EXCEPTIONS = {
    "BaseException", "BaseExceptionGroup", "Exception", "ExceptionGroup", "Warning",
    "ArithmeticError", "AssertionError", "AttributeError", "BufferError", "EOFError",
    "ImportError", "LookupError", "MemoryError", "NameError", "OSError", "ReferenceError",
    "RuntimeError", "StopIteration", "StopAsyncIteration", "SyntaxError", "SystemError",
    "TypeError", "ValueError", "UnicodeError", "Error", "Fault", "HTTPError",
}
SKIP_PARTS = {"__pycache__", "site-packages", "test", "tests", "idlelib", "turtledemo"}


def base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return base_name(node.value)
    return ""


def first_sentence(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    return " ".join(value.strip().split()).split(". ", 1)[0].strip() or fallback


def is_candidate(name: str, bases: list[str], known: set[str]) -> bool:
    if any(base in BASE_EXCEPTIONS or base in known for base in bases):
        return True
    return name.endswith(("Error", "Exception", "Warning", "Fault"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stdlib", type=Path, default=Path(sysconfig.get_paths()["stdlib"]))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    entries: list[dict[str, object]] = []
    used_ids: set[str] = set()
    for source in sorted(args.stdlib.rglob("*.py")):
        relative = source.relative_to(args.stdlib)
        if any(part in SKIP_PARTS or part.startswith(".") for part in relative.parts):
            continue
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        known = set(BASE_EXCEPTIONS)
        module = ".".join(relative.with_suffix("").parts)
        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or node.name.startswith("_"):
                continue
            bases = [base_name(base) for base in node.bases]
            if not is_candidate(node.name, bases, known):
                continue
            known.add(node.name)
            code = f"stdlib.{module}.{node.name}"
            entry_id = "py_stdlib_" + "_".join(part.lower().replace("-", "_").strip("_") for part in [*relative.with_suffix("").parts, node.name] if part.strip("_"))
            if entry_id in used_ids:
                continue
            used_ids.add(entry_id)
            is_warning = node.name.endswith("Warning") or "Warning" in bases
            title = first_sentence(ast.get_docstring(node), f"CPython standard-library exception class {node.name}.")
            entries.append({
                "id": entry_id,
                "language": "Python",
                "code": code,
                "category": "Runtime",
                "severity": "Warning" if is_warning else "Runtime Exception",
                "title": node.name,
                "description": f"{title}. Declared by CPython's standard library in {relative.as_posix()}; detailed usage guidance and examples are pending editorial review.",
                "bad_example": "# Registry-only record; a minimal reproduction is pending editorial review.",
                "good_example": "# Registry-only record; a source-backed repair is pending editorial review.",
                "version_introduced": f"Python {sys.version_info.major}.{sys.version_info.minor}",
                "version_deprecated": None,
                "source_url": f"{SOURCE_ROOT}/{relative.as_posix()}",
                "tier": 3,
                "frequency": "Uncommon",
                "situational_context": ["CPython standard library"],
                "interaction_types": ["runtime"],
                "related_errors": []
            })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(entries)} CPython standard-library exception classes from {args.stdlib}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
