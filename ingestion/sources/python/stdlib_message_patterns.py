#!/usr/bin/env python3
"""Extract stable, parameterized CPython standard-library raise-message patterns.

This adapter intentionally indexes only messages that are statically recoverable
from CPython's ``Lib`` tree.  It preserves the exception class and source module,
but normalizes interpolated values so records are useful search signatures rather
than one record per file path, identifier, or numeric value.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
import sysconfig
from pathlib import Path

SOURCE_ROOT = "https://github.com/python/cpython/blob/main/Lib"
SKIP_PARTS = {"__pycache__", "site-packages", "test", "tests", "idlelib", "turtledemo"}
EXCEPTION_NAMES = {
    "AssertionError", "AttributeError", "EOFError", "Exception", "ImportError", "IndexError",
    "KeyError", "LookupError", "MemoryError", "ModuleNotFoundError", "NameError", "NotImplementedError",
    "OSError", "OverflowError", "PermissionError", "ProcessLookupError", "RecursionError", "ReferenceError",
    "RuntimeError", "StopIteration", "SyntaxError", "SystemError", "TimeoutError", "TypeError", "ValueError",
    "UnicodeError", "UnicodeDecodeError", "UnicodeEncodeError", "UnicodeTranslateError", "Warning",
}


def called_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def render_message(node: ast.expr) -> str | None:
    """Return a stable template for conservative static string expressions."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                parts.append("{value}")
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = render_message(node.left), render_message(node.right)
        return f"{left or '{value}'}{right or '{value}'}"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        template = render_message(node.left)
        if template:
            return re.sub(r"%(?:\([^)]+\))?[#0 +\-]*\d*(?:\.\d+)?[diouxXeEfFgGcrs%]", "{value}", template)
    return None


def normalized_template(value: str) -> str:
    value = re.sub(r"\{\d+\}", "{value}", value)
    value = re.sub(r"(['\"]).*?\1", "{value}", value)
    value = re.sub(r"\b(?:0x[0-9a-fA-F]+|\d+)\b", "{n}", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:360]


def identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def category_and_severity(exception: str) -> tuple[str, str]:
    if exception in {"SyntaxError", "IndentationError", "TabError"}:
        return "Syntax", "Compiler Error"
    if exception in {"TypeError", "UnicodeError", "UnicodeDecodeError", "UnicodeEncodeError", "UnicodeTranslateError"}:
        return "Type System", "Runtime Exception"
    if exception == "MemoryError":
        return "Memory", "Runtime Exception"
    if exception in {"ImportError", "ModuleNotFoundError"}:
        return "Modules", "Runtime Exception"
    return "Runtime", "Warning" if exception.endswith("Warning") else "Runtime Exception"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stdlib", type=Path, default=Path(sysconfig.get_paths()["stdlib"]))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    entries: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for source in sorted(args.stdlib.rglob("*.py")):
        relative = source.relative_to(args.stdlib)
        if any(part in SKIP_PARTS or part.startswith(".") for part in relative.parts):
            continue
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        module = ".".join(relative.with_suffix("").parts)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
                continue
            exception = called_name(node.exc.func)
            if exception not in EXCEPTION_NAMES and not exception.endswith(("Error", "Exception", "Warning")):
                continue
            if not node.exc.args:
                continue
            raw_message = render_message(node.exc.args[0])
            if not raw_message:
                continue
            message = normalized_template(raw_message)
            if len(message) < 6 or not re.search(r"[A-Za-z]", message) or message == "{value}":
                continue
            identity = (exception, message)
            if identity in seen:
                continue
            seen.add(identity)
            digest = hashlib.sha1(f"{exception}\0{message}".encode("utf-8")).hexdigest()[:10]
            category, severity = category_and_severity(exception)
            entries.append({
                "id": f"py_pattern_{identifier(exception)}_{digest}",
                "language": "Python",
                "code": f"cpython::{module}::{exception}::{digest}",
                "category": category,
                "severity": severity,
                "title": f"{exception}: {message}",
                "description": f"CPython's standard library raises {exception} with this parameterized message pattern in {relative.as_posix()}. This source-qualified signature is not a distinct exception class; explanation, reproduction, and repair are pending editorial review.",
                "bad_example": "# Registry-only record; a minimal reproduction is pending editorial review.",
                "good_example": "# Registry-only record; a source-backed repair is pending editorial review.",
                "version_introduced": f"Python {sys.version_info.major}.{sys.version_info.minor}",
                "version_deprecated": None,
                "source_url": f"{SOURCE_ROOT}/{relative.as_posix()}#L{node.lineno}",
                "tier": 3,
                "frequency": "Uncommon",
                "situational_context": ["CPython standard library", f"module {module}"],
                "interaction_types": ["runtime"],
                "related_errors": [],
            })
    entries.sort(key=lambda entry: (str(entry["code"]), str(entry["id"])))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(entries)} parameterized CPython raise-message patterns from {args.stdlib}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
