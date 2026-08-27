#!/usr/bin/env python3
"""Extract public SpiderMonkey message definitions into the review queue."""
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

SOURCE_URL = "https://searchfox.org/mozilla-central/source/js/public/friend/ErrorNumbers.msg"
MESSAGE = re.compile(
    r"MSG_DEF\(\s*(?P<name>JSMSG_[A-Z0-9_]+)\s*,\s*\d+\s*,\s*(?P<exception>JSEXN_[A-Z0-9_]+)\s*,\s*(?P<literals>(?:\"(?:[^\"\\]|\\.)*\"\s*)+)\)",
    re.DOTALL,
)
EXCEPTIONS = {
    "JSEXN_ERR": "Error", "JSEXN_EVALERR": "EvalError", "JSEXN_RANGEERR": "RangeError",
    "JSEXN_REFERENCEERR": "ReferenceError", "JSEXN_SYNTAXERR": "SyntaxError", "JSEXN_TYPEERR": "TypeError",
    "JSEXN_URIERR": "URIError", "JSEXN_INTERNALERR": "InternalError", "JSEXN_AGGREGATEERR": "AggregateError",
}


def message_from_literals(value: str) -> str:
    return "".join(ast.literal_eval(item) for item in re.findall(r'"(?:[^"\\]|\\.)*"', value))


def identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def category_and_severity(exception: str) -> tuple[str, str]:
    if exception == "SyntaxError":
        return "Syntax", "Compiler Error"
    if exception in {"TypeError", "RangeError"}:
        return "Type System", "Runtime Exception"
    return "Runtime", "Runtime Exception"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contents = args.source.read_text(encoding="utf-8")
    entries: list[dict[str, object]] = []
    for match in MESSAGE.finditer(contents):
        name = match.group("name")
        exception = EXCEPTIONS.get(match.group("exception"), "Error")
        template = re.sub(r"\{\d+\}", "{value}", message_from_literals(match.group("literals"))).strip()
        if not template or name == "JSMSG_NOT_AN_ERROR":
            continue
        category, severity = category_and_severity(exception)
        entries.append({
            "id": f"js_spidermonkey_{identifier(name.removeprefix('JSMSG_'))}",
            "language": "JavaScript",
            "code": f"spidermonkey::{exception}::{name}",
            "category": category,
            "severity": severity,
            "title": f"{exception}: {template}",
            "description": f"SpiderMonkey {exception} message definition `{name}` from Mozilla's public error-number registry. This source-qualified diagnostic still needs curated context, reproduction, and repair guidance.",
            "bad_example": "// Registry-only record; a minimal reproduction is pending editorial review.",
            "good_example": "// Registry-only record; a source-backed repair is pending editorial review.",
            "version_introduced": None,
            "version_deprecated": None,
            "source_url": SOURCE_URL,
            "tier": 3,
            "frequency": "Uncommon",
            "situational_context": ["SpiderMonkey JavaScript runtime", "browser or embedded runtime"],
            "interaction_types": ["runtime"],
            "related_errors": [],
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(entries)} SpiderMonkey message definitions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
