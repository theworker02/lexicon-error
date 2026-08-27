#!/usr/bin/env python3
"""Extract TypeScript's official compiler diagnostic registry."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

SOURCE_URL = "https://github.com/microsoft/TypeScript/blob/main/src/compiler/diagnosticMessages.json"


def category_for(message: str, code: int) -> str:
    text = message.lower()
    if code < 2000 or any(word in text for word in ("token", "parser", "syntax", "expected")):
        return "Syntax"
    if any(word in text for word in ("type", "assignable", "property", "generic", "overload")):
        return "Type System"
    if any(word in text for word in ("module", "import", "export", "reference")):
        return "Linker"
    return "Compiler"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path, help="Official diagnosticMessages.json snapshot")
    parser.add_argument("--typescript-module", type=Path, help="Local official TypeScript compiler JS module")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.source:
        records = json.loads(args.source.read_text(encoding="utf-8")).items()
    elif args.typescript_module:
        expression = "const ts=require(process.argv[1]); console.log(JSON.stringify(Object.values(ts.Diagnostics || {})));"
        output = subprocess.check_output(["node", "-e", expression, str(args.typescript_module.resolve())], text=True)
        diagnostics = json.loads(output)
        records = ((diagnostic["message"], {"code": diagnostic["code"], "category": "Error" if diagnostic["category"] == 1 else "Warning"}) for diagnostic in diagnostics)
    else:
        parser.error("provide an official JSON snapshot or --typescript-module")
    entries = []
    for message, metadata in records:
        code = metadata.get("code")
        if not isinstance(code, int):
            continue
        category = metadata.get("category", "Error")
        severity = "Compiler Error" if category == "Error" else "Warning"
        entries.append({"id": f"ts_{code}", "language": "TypeScript", "code": f"TS{code}",
          "category": category_for(message, code), "severity": severity, "title": message,
          "description": "Official TypeScript compiler diagnostic. Add a reviewed explanation and runnable repair.",
          "bad_example": "// Add a minimal reproduction.", "good_example": "// Add the corresponding repair.",
          "version_introduced": None, "version_deprecated": None, "source_url": SOURCE_URL})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(entries)} TypeScript diagnostics.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
