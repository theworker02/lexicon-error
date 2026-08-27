"""Shared normalized knowledge-layer support for dataset builds, CLI, and local API."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
DATASET_VERSION = "2026.08"
MAX_PASTED_ERROR_BYTES = 16 * 1024

KNOWLEDGE_SCHEMA = """
CREATE TABLE languages (id TEXT PRIMARY KEY NOT NULL, name TEXT NOT NULL, ecosystem TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE tools (id TEXT PRIMARY KEY NOT NULL, language_id TEXT NOT NULL REFERENCES languages(id), name TEXT NOT NULL, kind TEXT NOT NULL);
CREATE TABLE concepts (id TEXT PRIMARY KEY NOT NULL, name TEXT NOT NULL, classification TEXT NOT NULL, description TEXT NOT NULL);
CREATE TABLE root_causes (id TEXT PRIMARY KEY NOT NULL, name TEXT NOT NULL);
CREATE TABLE error_metadata (
  entry_id TEXT PRIMARY KEY NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
  canonical_id TEXT NOT NULL UNIQUE, language_id TEXT NOT NULL REFERENCES languages(id), tool_id TEXT NOT NULL REFERENCES tools(id),
  classifications TEXT NOT NULL, normalized_severity TEXT NOT NULL, canonical_message TEXT NOT NULL, summary TEXT NOT NULL,
  when_it_occurs TEXT NOT NULL DEFAULT '[]', causes TEXT NOT NULL DEFAULT '[]', fixes TEXT NOT NULL DEFAULT '[]', prevention TEXT,
  explanation_of_example TEXT, tags TEXT NOT NULL DEFAULT '[]', aliases TEXT NOT NULL DEFAULT '[]', fingerprint TEXT NOT NULL,
  signature_kind TEXT NOT NULL DEFAULT 'identifier', signature_pattern TEXT, platforms TEXT NOT NULL DEFAULT '[]', provenance TEXT NOT NULL,
  verification_status TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX error_metadata_canonical_id_idx ON error_metadata(canonical_id);
CREATE INDEX error_metadata_tool_id_idx ON error_metadata(tool_id);
CREATE INDEX error_metadata_fingerprint_idx ON error_metadata(fingerprint);
CREATE TABLE error_concepts (entry_id TEXT NOT NULL REFERENCES entries(id) ON DELETE CASCADE, concept_id TEXT NOT NULL REFERENCES concepts(id), PRIMARY KEY (entry_id, concept_id));
CREATE TABLE error_relationships (
  source_entry_id TEXT NOT NULL REFERENCES entries(id) ON DELETE CASCADE, target_entry_id TEXT NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
  relationship_type TEXT NOT NULL CHECK(relationship_type IN ('similar_to','caused_by','commonly_followed_by','often_confused_with','language_equivalent','subclass_of','superseded_by','related_to','can_cause')),
  PRIMARY KEY (source_entry_id, target_entry_id, relationship_type)
);
"""


def load_catalog(name: str) -> list[dict[str, Any]]:
    return json.loads((ROOT / "data" / "knowledge" / name).read_text(encoding="utf-8"))


def language_id(language: str) -> str:
    names = {"C++": "cpp", "C#": "csharp", "F#": "fsharp", "Visual Basic / VB.NET": "vbnet", "Shell / Bash": "bash", "Shell/Bash": "bash", "ROCm / HIP": "rocm-hip"}
    return names.get(language, "".join(char.lower() for char in language if char.isalnum() or char == "-"))


def default_tool(language: str, code: str) -> str:
    if language == "rust" and code.startswith("clippy::"):
        return "clippy"
    if language == "javascript" and code.startswith("v8::"):
        return "v8"
    if language == "javascript" and code.startswith("mdn::"):
        return "browser"
    if language == "javascript" and code.startswith("spidermonkey::"):
        return "spidermonkey"
    if language == "csharp" and code.startswith("System."):
        return "dotnet"
    return {
        "ada": "gnat", "agda": "agda", "bash": "bash", "brainfuck": "brainfuck-interpreter", "c": "gcc", "cairo": "cairo-compiler", "cuda": "cuda-runtime",
        "cobol": "gnucobol", "cpp": "clang", "crystal": "crystal", "csharp": "roslyn", "d": "dmd", "elm": "elm-compiler",
        "css": "css-validator", "erlang": "erlang-runtime", "fortran": "gfortran", "go": "go-compiler", "html": "html-validator", "idris": "idris2", "java": "javac", "javascript": "nodejs",
        "kotlin": "kotlin-compiler", "move": "move-compiler", "nim": "nim", "opencl": "opencl-runtime", "purescript": "purescript", "python": "cpython", "r": "r-runtime",
        "racket": "racket", "rocm-hip": "hip-runtime", "rust": "rustc", "scheme": "scheme-runtime", "sql": "sqlite", "swift": "swiftc", "typescript": "tsc", "unlambda": "unlambda-interpreter",
        "vulkan": "vulkan-runtime", "vyper": "vyper", "whitespace": "whitespace-interpreter",
    }.get(language, "custom-tool")


def slug(value: str) -> str:
    output, separator = [], False
    for char in value.lower():
        if char.isalnum():
            output.append(char); separator = False
        elif not separator:
            output.append("-"); separator = True
    return "".join(output).strip("-")


def normalized_severity(value: str) -> str:
    return {"Fatal": "fatal", "Warning": "warning", "Linter Rule": "information", "Undefined Behavior": "error", "Runtime Exception": "error", "Compiler Error": "error"}.get(value, "information")


def classifications(category: str, severity: str) -> list[str]:
    value = category.lower()
    if "syntax" in value: primary = "syntax-error"
    elif "type" in value: primary = "type-error"
    elif "memory" in value: primary = "memory-error"
    elif "concurrency" in value: primary = "concurrency-error"
    elif "link" in value: primary = "linker-error"
    elif "module" in value: primary = "module-error"
    elif "import" in value: primary = "import-error"
    elif "runtime" in value: primary = "runtime-error"
    elif "security" in value: primary = "security-error"
    elif "network" in value: primary = "network-error"
    elif "database" in value: primary = "database-error"
    elif "io" in value: primary = "io-error"
    else: primary = "compilation-error"
    result = [primary]
    if severity == "Runtime Exception": result.append("exception")
    if severity == "Warning": result.append("warning")
    if severity == "Linter Rule": result.append("linter-diagnostic")
    return result


def concepts_for(entry: sqlite3.Row, classes: list[str]) -> list[str]:
    text = f"{entry['code']} {entry['title']} {entry['description']}".lower()
    result: list[str] = []
    if "moved value" in text or "borrow" in text: result.append("borrow-violation")
    if "null" in text or "undefined" in text: result.append("null-access")
    if any(token in text for token in ("not assignable", "implicitly convert", "type mismatch")): result.append("type-mismatch")
    if any(token in text for token in ("not found", "undeclared", "cannot find name")): result.append("undefined-identifier")
    if any(token in text for token in ("module", "import", "assembly reference")): result.append("missing-module")
    if "deadlock" in text: result.append("deadlock")
    if "duplicate" in text: result.append("duplicate-declaration")
    if "syntax-error" in classes: result.append("invalid-syntax")
    return sorted(set(result))


def fingerprint(value: str) -> str:
    output: list[str] = []
    quote, inserted = False, False
    for char in value.lower()[:512]:
        if char in "'\"`":
            quote = not quote
            if quote and not inserted: output.append("{value}"); inserted = True
        elif quote:
            continue
        elif char.isdigit():
            if not "".join(output).endswith("{n}"): output.append("{n}")
        elif char.isspace():
            if not output or output[-1] != " ": output.append(" ")
        else: output.append(char)
    return "".join(output).strip()


def seed_catalogs(connection: sqlite3.Connection) -> None:
    for table, filename, columns in [
        ("languages", "languages.json", ("id", "name", "ecosystem", "status")),
        ("tools", "tools.json", ("id", "language_id", "name", "kind")),
        ("concepts", "concepts.json", ("id", "name", "classification", "description")),
        ("root_causes", "root-causes.json", ("id", "name")),
    ]:
        for record in load_catalog(filename):
            columns_sql = ", ".join(columns)
            values_sql = ", ".join(f":{column}" for column in columns)
            updates = ", ".join(f"{column}=excluded.{column}" for column in columns if column != "id")
            connection.execute(f"INSERT INTO {table} ({columns_sql}) VALUES ({values_sql}) ON CONFLICT(id) DO UPDATE SET {updates}", record)


def populate_knowledge(connection: sqlite3.Connection) -> None:
    connection.executescript(KNOWLEDGE_SCHEMA)
    seed_catalogs(connection)
    connection.row_factory = sqlite3.Row
    entries = connection.execute("SELECT * FROM entries").fetchall()
    for entry in entries:
        lang_id = language_id(entry["language"])
        connection.execute("INSERT OR IGNORE INTO languages (id, name, ecosystem, status) VALUES (?, ?, 'Imported/custom language', 'custom')", (lang_id, entry["language"]))
        tool_id = default_tool(lang_id, entry["code"])
        connection.execute("INSERT OR IGNORE INTO tools (id, language_id, name, kind) VALUES (?, ?, ?, 'toolchain')", (tool_id, lang_id, f"{entry['language']} toolchain"))
        classes = classifications(entry["category"], entry["severity"])
        concept_ids = concepts_for(entry, classes)
        cause_ids = {"undefined-identifier": "incorrect-scope", "type-mismatch": "invalid-type", "missing-module": "missing-dependency", "invalid-syntax": "invalid-syntax"}
        causes = [{"id": cause_ids[item], "likelihood": "common"} for item in concept_ids if item in cause_ids]
        generated = entry["title"] == "Needs editorial enrichment" or "Add a minimal reproduction" in entry["bad_example"] or "Registry-only record" in entry["bad_example"]
        canonical_message = entry["title"] if any(char.isspace() for char in entry["code"]) else f"{entry['code']}: {entry['title']}"
        metadata = {
            "entry_id": entry["id"], "canonical_id": f"{lang_id}.{tool_id}.{slug(entry['code'])}", "language_id": lang_id, "tool_id": tool_id,
            "classifications": json.dumps(classes), "normalized_severity": normalized_severity(entry["severity"]), "canonical_message": canonical_message,
            "summary": entry["description"], "when_it_occurs": entry["situational_context"], "causes": json.dumps(causes), "tags": json.dumps([entry["category"], entry["severity"]]),
            "aliases": json.dumps([entry["code"], entry["title"]]), "fingerprint": fingerprint(entry["title"]),
            "provenance": json.dumps({"source_type": "official-registry-metadata" if generated else "curated-entry", "source_authority": "Official" if generated else "Contributor reviewed", "review_state": "generated-draft" if generated else "reviewed", "source_url": entry["source_url"], "source_title": entry["title"], "dataset_version": DATASET_VERSION}),
            "verification_status": "Needs Review" if generated else "Verified",
        }
        connection.execute("""INSERT OR IGNORE INTO error_metadata (entry_id, canonical_id, language_id, tool_id, classifications, normalized_severity, canonical_message, summary, when_it_occurs, causes, fixes, prevention, explanation_of_example, tags, aliases, fingerprint, signature_kind, signature_pattern, platforms, provenance, verification_status, updated_at)
          VALUES (:entry_id, :canonical_id, :language_id, :tool_id, :classifications, :normalized_severity, :canonical_message, :summary, :when_it_occurs, :causes, '[]', NULL, NULL, :tags, :aliases, :fingerprint, 'identifier', NULL, '[]', :provenance, :verification_status, '2026-08-27')""", metadata)
        for concept_id in concept_ids:
            connection.execute("INSERT OR IGNORE INTO error_concepts (entry_id, concept_id) VALUES (?, ?)", (entry["id"], concept_id))
        for related in json.loads(entry["related_errors"]):
            connection.execute("""INSERT OR IGNORE INTO error_relationships (source_entry_id, target_entry_id, relationship_type)
              SELECT ?, id, 'related_to' FROM entries WHERE id = ?""", (entry["id"], related))


def sanitize_pasted_error(message: str) -> tuple[str, bool]:
    encoded = message.encode("utf-8")
    if len(encoded) > MAX_PASTED_ERROR_BYTES:
        raise ValueError(f"Paste is too large; limit error text to {MAX_PASTED_ERROR_BYTES} bytes")
    redacted, output = False, []
    for raw_line in message.replace("\r\n", "\n").splitlines()[-80:]:
        line, lower = raw_line.strip(), raw_line.lower()
        if any(marker in lower for marker in ("api_key", "apikey", "authorization:", "password=", "token=", "secret=")):
            output.append("[redacted secret-bearing line]"); redacted = True
        elif line.startswith(("C:\\", "/home/", "/users/", "/private/")):
            output.append("[redacted local path]"); redacted = True
        elif "://" in line and "@" in line:
            output.append("[redacted credential-bearing URL]"); redacted = True
        elif line:
            output.append(line)
    return "\n".join(output), redacted


def likely_language(message: str) -> str | None:
    value = message.lower()
    if "error[" in value or "rustc" in value: return "Rust"
    if "ts" in value and "error" in value: return "TypeScript"
    if "cs" in value and "error" in value: return "C#"
    if "traceback" in value or "nameerror" in value: return "Python"
    if "panic:" in value or "goroutine" in value: return "Go"
    if "exception in thread" in value: return "Java"
    return None


def detect(connection: sqlite3.Connection, message: str) -> dict[str, Any]:
    normalized, redacted = sanitize_pasted_error(message)
    hint = likely_language(normalized)
    tokens = sorted({token for token in _split_identifier_tokens(normalized) if len(token) >= 3})[:64]
    matches: list[dict[str, Any]] = []
    for token in tokens:
        rows = connection.execute("""SELECT e.id, m.canonical_id, e.language, m.tool_id, e.code
          FROM entries e JOIN error_metadata m ON m.entry_id=e.id
          WHERE lower(e.code)=lower(?) OR lower(e.title)=lower(?) LIMIT 8""", (token, token)).fetchall()
        for row in rows:
            if hint and row[2] != hint: continue
            if any(item["entry_id"] == row[0] for item in matches): continue
            exact = row[4].lower() == token.lower()
            matches.append({"entry_id": row[0], "canonical_id": row[1], "language": row[2], "tool": row[3], "code": row[4], "confidence": 0.99 if exact else 0.86, "confidence_label": "Exact Match" if exact else "Likely Match"})
    return {"normalized_message": normalized, "redacted": redacted, "matches": sorted(matches, key=lambda item: item["confidence"], reverse=True)[:5]}


def _split_identifier_tokens(value: str) -> list[str]:
    token, output = [], []
    for char in value:
        if char.isalnum() or char == "_": token.append(char)
        elif token: output.append("".join(token)); token = []
    if token: output.append("".join(token))
    return output


def statistics(connection: sqlite3.Connection) -> dict[str, Any]:
    return {
        "dataset_version": DATASET_VERSION,
        "diagnostics": connection.execute("SELECT COUNT(*) FROM entries").fetchone()[0],
        "languages": connection.execute("SELECT COUNT(DISTINCT language_id) FROM error_metadata").fetchone()[0],
        "tools": connection.execute("SELECT COUNT(*) FROM tools WHERE EXISTS (SELECT 1 FROM error_metadata WHERE tool_id=tools.id)").fetchone()[0],
        "concepts": connection.execute("SELECT COUNT(*) FROM concepts").fetchone()[0],
        "verified": connection.execute("SELECT COUNT(*) FROM error_metadata WHERE verification_status IN ('Official', 'Verified', 'Community Verified')").fetchone()[0],
        "needs_review": connection.execute("SELECT COUNT(*) FROM error_metadata WHERE verification_status = 'Needs Review'").fetchone()[0],
        "with_examples": connection.execute("SELECT COUNT(*) FROM entries WHERE bad_example NOT LIKE '%Add a minimal reproduction%' AND bad_example NOT LIKE '%Registry-only record%'").fetchone()[0],
        "by_language": [{"language": row[0], "diagnostics": row[1]} for row in connection.execute("SELECT language, COUNT(*) AS diagnostics FROM entries GROUP BY language ORDER BY diagnostics DESC")],
    }


def validate_knowledge(connection: sqlite3.Connection) -> list[str]:
    checks = {
        "metadata missing for entries": "SELECT COUNT(*) FROM entries e LEFT JOIN error_metadata m ON m.entry_id=e.id WHERE m.entry_id IS NULL",
        "metadata references unknown languages": "SELECT COUNT(*) FROM error_metadata m LEFT JOIN languages l ON l.id=m.language_id WHERE l.id IS NULL",
        "metadata references unknown tools": "SELECT COUNT(*) FROM error_metadata m LEFT JOIN tools t ON t.id=m.tool_id WHERE t.id IS NULL",
        "broken concept relationships": "SELECT COUNT(*) FROM error_concepts ec LEFT JOIN concepts c ON c.id=ec.concept_id WHERE c.id IS NULL",
        "broken error relationships": "SELECT COUNT(*) FROM error_relationships r LEFT JOIN entries e ON e.id=r.target_entry_id WHERE e.id IS NULL",
    }
    return [f"{label}: {connection.execute(query).fetchone()[0]}" for label, query in checks.items() if connection.execute(query).fetchone()[0]]
