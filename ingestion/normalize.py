"""Shared cleaning and schema-shaping helpers for official-source parsers."""
from __future__ import annotations

import html
import re
from typing import Any

_WHITESPACE = re.compile(r"[ \t]+")
_BLANK_LINES = re.compile(r"\n{3,}")


def clean_text(value: str) -> str:
    """Decode entities and normalize prose without destroying code formatting."""
    value = html.unescape(value).replace("\r\n", "\n")
    value = "\n".join(_WHITESPACE.sub(" ", line).strip() for line in value.splitlines())
    return _BLANK_LINES.sub("\n\n", value).strip()


def entry(**values: Any) -> dict[str, Any]:
    required = {"id", "language", "code", "category", "severity", "title", "description", "bad_example", "good_example"}
    missing = required - values.keys()
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")
    values["description"] = clean_text(values["description"])
    if values.get("source_reference") and not values.get("source_url"):
        values["source_url"] = values.pop("source_reference")
    elif values.get("source_reference") == values.get("source_url"):
        values.pop("source_reference")
    for field in ("version_introduced", "version_deprecated", "source_url"):
        values.setdefault(field, None)
    return values
