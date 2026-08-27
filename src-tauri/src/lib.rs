use rusqlite::{params, params_from_iter, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use std::{collections::HashSet, fs, path::{Path, PathBuf}, sync::Mutex};
use tauri::{AppHandle, Manager, State};

const SEED_DATA: &str = include_str!("../../data/seed.json");
const REVIEW_DATA: &[&str] = &[
    include_str!("../../data/review/rust-error-stubs.json"),
    include_str!("../../data/review/csharp-preprocessor-stubs.json"),
    include_str!("../../data/review/csharp-roslyn-error-codes.json"),
    include_str!("../../data/review/python-exception-stubs.json"),
    include_str!("../../data/review/python-stdlib-exceptions.json"),
    include_str!("../../data/review/python-stdlib-message-patterns.json"),
    include_str!("../../data/review/typescript-diagnostics.json"),
    include_str!("../../data/review/javac-diagnostics.json"),
    include_str!("../../data/review/clang-sema-diagnostics.json"),
    include_str!("../../data/review/node-error-codes.json"),
    include_str!("../../data/review/v8-message-templates.json"),
    include_str!("../../data/review/spidermonkey-message-definitions.json"),
    include_str!("../../data/review/mdn-javascript-errors.json"),
    include_str!("../../data/review/go-type-errors.json"),
    include_str!("../../data/review/rustc-lints.json"),
    include_str!("../../data/review/clippy-lints.json"),
    include_str!("../../data/review/user-attributed-candidates.json"),
    include_str!("../../data/review/dotnet-runtime-exceptions.json"),
    include_str!("../../data/review/kotlin-compiler-diagnostics.json"),
    include_str!("../../data/review/sqlite-result-codes.json"),
    include_str!("../../data/review/r-runtime-messages.json"),
    include_str!("../../data/review/niche-language-examples.json"),
    include_str!("../../data/review/cuda-runtime-errors.json"),
    include_str!("../../data/review/hip-runtime-errors.json"),
    include_str!("../../data/review/vulkan-result-codes.json"),
    include_str!("../../data/review/opencl-error-codes.json"),
];
const LANGUAGE_DATA: &str = include_str!("../../data/knowledge/languages.json");
const TOOL_DATA: &str = include_str!("../../data/knowledge/tools.json");
const CONCEPT_DATA: &str = include_str!("../../data/knowledge/concepts.json");
const ROOT_CAUSE_DATA: &str = include_str!("../../data/knowledge/root-causes.json");
const COVERAGE_TARGET_DATA: &str = include_str!("../../data/knowledge/coverage-targets.json");
const MAX_RESULTS: usize = 100;
const MAX_PASTED_ERROR_BYTES: usize = 16 * 1024;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ErrorEntry {
    id: String,
    language: String,
    code: String,
    category: String,
    severity: String,
    title: String,
    description: String,
    bad_example: String,
    good_example: String,
    version_introduced: Option<String>,
    version_deprecated: Option<String>,
    #[serde(alias = "source_reference")]
    source_url: Option<String>,
    #[serde(default = "default_tier")]
    tier: i32,
    #[serde(default = "default_frequency")]
    frequency: String,
    #[serde(default)]
    situational_context: Vec<String>,
    #[serde(default)]
    interaction_types: Vec<String>,
    #[serde(default)]
    related_errors: Vec<String>,
    #[serde(default)]
    state_snapshot: Option<StateSnapshot>,
    #[serde(skip_serializing_if = "Option::is_none")]
    score: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct StateVariable { name: String, value: String, status: String }

#[derive(Debug, Clone, Serialize, Deserialize)]
struct StateSnapshot { event: String, frames: Vec<String>, variables: Vec<StateVariable> }

#[derive(Debug, Deserialize)]
struct KnowledgeLanguage { id: String, name: String, ecosystem: String, status: String }

#[derive(Debug, Deserialize)]
struct KnowledgeTool { id: String, language_id: String, name: String, kind: String }

#[derive(Debug, Deserialize)]
struct KnowledgeConcept { id: String, name: String, classification: String, description: String }

#[derive(Debug, Deserialize)]
struct RootCause { id: String, name: String }

#[derive(Debug, Deserialize)]
struct CoverageTarget { language_id: String, target: i64 }

#[derive(Serialize)]
struct LanguageProfile { id: String, name: String, ecosystem: String, status: String, diagnostic_count: i64, tool_count: i64 }

#[derive(Serialize)]
struct ToolProfile { id: String, language_id: String, name: String, kind: String, diagnostic_count: i64 }

#[derive(Serialize)]
struct ConceptProfile { id: String, name: String, classification: String, description: String, diagnostic_count: i64 }

#[derive(Serialize)]
struct CoverageQuality { verified: f64, explanations: f64, examples: f64, fixes: f64, sources: f64, versions: f64, relationships: f64 }

#[derive(Serialize)]
struct CoverageProfile { language_id: String, language: String, records: i64, target: i64, progress: f64, tools: i64, quality: CoverageQuality, tier: String }

#[derive(Serialize)]
struct ErrorMetadata {
    entry_id: String, canonical_id: String, language_id: String, tool_id: String,
    classifications: Vec<String>, normalized_severity: String, canonical_message: String,
    summary: String, when_it_occurs: Vec<String>, causes: Vec<serde_json::Value>,
    fixes: Vec<serde_json::Value>, prevention: Option<String>, explanation_of_example: Option<String>,
    tags: Vec<String>, aliases: Vec<String>, fingerprint: String, signature_kind: String,
    signature_pattern: Option<String>, platforms: Vec<String>, provenance: serde_json::Value,
    verification_status: String, updated_at: String,
}

#[derive(Serialize)]
struct DetectionMatch { entry_id: String, canonical_id: String, language: String, tool_id: String, code: String, confidence: f64, confidence_label: String }

#[derive(Serialize)]
struct DetectionResult { normalized_message: String, matches: Vec<DetectionMatch>, redacted: bool }

fn default_tier() -> i32 { 1 }
fn default_frequency() -> String { "Common".to_string() }

#[derive(Debug, Deserialize)]
struct Filters {
    languages: Vec<String>,
    categories: Vec<String>,
    severities: Vec<String>,
    frequencies: Vec<String>,
    interactions: Vec<String>,
}

#[derive(Serialize)]
struct Facets {
    languages: Vec<String>,
    categories: Vec<String>,
    severities: Vec<String>,
    frequencies: Vec<String>,
    interactions: Vec<String>,
    total: i64,
}

#[derive(Serialize)]
struct MatrixCell { language: String, category: String, frequency: String, count: i64 }

#[derive(Debug, Serialize)]
struct CountBucket { label: String, count: i64 }

#[derive(Debug, Serialize)]
struct RelatedEntry {
    id: String, language: String, code: String, title: String,
    category: String, severity: String, frequency: String,
}

#[derive(Debug, Serialize)]
struct EntryInsights {
    language_total: i64,
    category_total: i64,
    frequency_distribution: Vec<CountBucket>,
    category_distribution: Vec<CountBucket>,
    related_entries: Vec<RelatedEntry>,
}

struct Database(Mutex<Connection>);

fn database_path(app: &AppHandle) -> Result<PathBuf, String> {
    let data_dir = app.path().app_data_dir().map_err(|error| error.to_string())?;
    fs::create_dir_all(&data_dir).map_err(|error| format!("Could not create application data directory: {error}"))?;
    Ok(data_dir.join("lexicon-error.db"))
}

fn contribution_dir(app: &AppHandle) -> Result<PathBuf, String> {
    let dir = app.path().app_data_dir().map_err(|error| error.to_string())?.join("contributions");
    fs::create_dir_all(&dir).map_err(|error| format!("Could not create contributions directory: {error}"))?;
    Ok(dir)
}

fn initialize_database(path: &Path) -> Result<Connection, String> {
    let connection = Connection::open(path).map_err(|error| error.to_string())?;
    connection.execute_batch(
        "PRAGMA journal_mode = WAL;
         PRAGMA foreign_keys = ON;
         PRAGMA synchronous = NORMAL;
         CREATE TABLE IF NOT EXISTS entries (
            id TEXT PRIMARY KEY NOT NULL,
            language TEXT NOT NULL,
            code TEXT NOT NULL,
            category TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            bad_example TEXT NOT NULL,
            good_example TEXT NOT NULL,
            version_introduced TEXT,
            version_deprecated TEXT,
            source_url TEXT,
            tier INTEGER NOT NULL DEFAULT 1,
            frequency TEXT NOT NULL DEFAULT 'Common',
            situational_context TEXT NOT NULL DEFAULT '[]',
            interaction_types TEXT NOT NULL DEFAULT '[]',
            related_errors TEXT NOT NULL DEFAULT '[]',
            state_snapshot TEXT
         );
         CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
            code, title, description, language, category,
            content='entries', content_rowid='rowid', tokenize='unicode61 remove_diacritics 2'
         );
         CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
           INSERT INTO entries_fts(rowid, code, title, description, language, category)
           VALUES (new.rowid, new.code, new.title, new.description, new.language, new.category);
         END;
         CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
           INSERT INTO entries_fts(entries_fts, rowid, code, title, description, language, category)
           VALUES ('delete', old.rowid, old.code, old.title, old.description, old.language, old.category);
         END;
         CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE ON entries BEGIN
           INSERT INTO entries_fts(entries_fts, rowid, code, title, description, language, category)
           VALUES ('delete', old.rowid, old.code, old.title, old.description, old.language, old.category);
           INSERT INTO entries_fts(rowid, code, title, description, language, category)
           VALUES (new.rowid, new.code, new.title, new.description, new.language, new.category);
         END;
         CREATE TABLE IF NOT EXISTS languages (
            id TEXT PRIMARY KEY NOT NULL, name TEXT NOT NULL, ecosystem TEXT NOT NULL, status TEXT NOT NULL
         );
         CREATE TABLE IF NOT EXISTS tools (
            id TEXT PRIMARY KEY NOT NULL, language_id TEXT NOT NULL REFERENCES languages(id), name TEXT NOT NULL, kind TEXT NOT NULL
         );
         CREATE TABLE IF NOT EXISTS concepts (
            id TEXT PRIMARY KEY NOT NULL, name TEXT NOT NULL, classification TEXT NOT NULL, description TEXT NOT NULL
         );
         CREATE TABLE IF NOT EXISTS root_causes (
            id TEXT PRIMARY KEY NOT NULL, name TEXT NOT NULL
         );
         CREATE TABLE IF NOT EXISTS error_metadata (
            entry_id TEXT PRIMARY KEY NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
            canonical_id TEXT NOT NULL UNIQUE, language_id TEXT NOT NULL REFERENCES languages(id), tool_id TEXT NOT NULL REFERENCES tools(id),
            classifications TEXT NOT NULL, normalized_severity TEXT NOT NULL, canonical_message TEXT NOT NULL,
            summary TEXT NOT NULL, when_it_occurs TEXT NOT NULL DEFAULT '[]', causes TEXT NOT NULL DEFAULT '[]', fixes TEXT NOT NULL DEFAULT '[]',
            prevention TEXT, explanation_of_example TEXT, tags TEXT NOT NULL DEFAULT '[]', aliases TEXT NOT NULL DEFAULT '[]',
            fingerprint TEXT NOT NULL, signature_kind TEXT NOT NULL DEFAULT 'identifier', signature_pattern TEXT,
            platforms TEXT NOT NULL DEFAULT '[]', provenance TEXT NOT NULL, verification_status TEXT NOT NULL, updated_at TEXT NOT NULL
         );
         CREATE INDEX IF NOT EXISTS error_metadata_canonical_id_idx ON error_metadata(canonical_id);
         CREATE INDEX IF NOT EXISTS error_metadata_tool_id_idx ON error_metadata(tool_id);
         CREATE INDEX IF NOT EXISTS error_metadata_fingerprint_idx ON error_metadata(fingerprint);
         CREATE TABLE IF NOT EXISTS error_concepts (
            entry_id TEXT NOT NULL REFERENCES entries(id) ON DELETE CASCADE, concept_id TEXT NOT NULL REFERENCES concepts(id),
            PRIMARY KEY (entry_id, concept_id)
         );
         CREATE TABLE IF NOT EXISTS error_relationships (
            source_entry_id TEXT NOT NULL REFERENCES entries(id) ON DELETE CASCADE, target_entry_id TEXT NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
            relationship_type TEXT NOT NULL CHECK(relationship_type IN ('similar_to','caused_by','commonly_followed_by','often_confused_with','language_equivalent','subclass_of','superseded_by','related_to','can_cause')),
            PRIMARY KEY (source_entry_id, target_entry_id, relationship_type)
         );"
    ).map_err(|error| error.to_string())?;

    ensure_phase_two_columns(&connection)?;
    let count: i64 = connection.query_row("SELECT COUNT(*) FROM entries", [], |row| row.get(0)).map_err(|error| error.to_string())?;
    if count == 0 {
        for source in REVIEW_DATA {
            let entries: Vec<ErrorEntry> = serde_json::from_str(source).map_err(|error| format!("Invalid bundled review data: {error}"))?;
            for entry in entries { validate_entry(&entry)?; upsert_entry(&connection, &entry)?; }
        }
        let seed_entries: Vec<ErrorEntry> = serde_json::from_str(SEED_DATA).map_err(|error| format!("Invalid bundled seed data: {error}"))?;
        for entry in seed_entries { validate_entry(&entry)?; upsert_entry(&connection, &entry)?; }
    }
    initialize_knowledge_graph(&connection)?;
    Ok(connection)
}

fn ensure_phase_two_columns(connection: &Connection) -> Result<(), String> {
    let mut statement = connection.prepare("PRAGMA table_info(entries)").map_err(|error| error.to_string())?;
    let existing = statement.query_map([], |row| row.get::<_, String>(1)).map_err(|error| error.to_string())?.collect::<Result<HashSet<_>, _>>().map_err(|error| error.to_string())?;
    for (name, definition) in [
        ("tier", "INTEGER NOT NULL DEFAULT 1"), ("frequency", "TEXT NOT NULL DEFAULT 'Common'"),
        ("situational_context", "TEXT NOT NULL DEFAULT '[]'"), ("interaction_types", "TEXT NOT NULL DEFAULT '[]'"),
        ("related_errors", "TEXT NOT NULL DEFAULT '[]'"), ("state_snapshot", "TEXT")
    ] {
        if !existing.contains(name) { connection.execute_batch(&format!("ALTER TABLE entries ADD COLUMN {name} {definition}")) .map_err(|error| error.to_string())?; }
    }
    Ok(())
}

fn normalized_language_id(language: &str) -> String {
    match language {
        "C++" => "cpp".to_string(), "C#" => "csharp".to_string(), "F#" => "fsharp".to_string(),
        "Visual Basic / VB.NET" => "vbnet".to_string(), "Shell/Bash" | "Shell / Bash" => "bash".to_string(),
        value => value.to_ascii_lowercase().chars().filter(|character| character.is_ascii_alphanumeric() || *character == '-').collect(),
    }
}

fn default_tool_for(entry: &ErrorEntry, language_id: &str) -> &'static str {
    match (language_id, entry.code.as_str()) {
        ("rust", code) if code.starts_with("clippy::") => "clippy",
        ("javascript", code) if code.starts_with("v8::") => "v8",
        ("javascript", code) if code.starts_with("mdn::") => "browser",
        ("javascript", code) if code.starts_with("spidermonkey::") => "spidermonkey",
        ("csharp", code) if code.starts_with("System.") => "dotnet",
        _ => match language_id {
        "ada" => "gnat", "agda" => "agda", "bash" => "bash", "brainfuck" => "brainfuck-interpreter", "c" => "gcc", "cairo" => "cairo-compiler", "cuda" => "cuda-runtime",
        "cobol" => "gnucobol", "cpp" => "clang", "crystal" => "crystal", "csharp" => "roslyn", "d" => "dmd", "elm" => "elm-compiler",
        "css" => "css-validator", "erlang" => "erlang-runtime", "fortran" => "gfortran", "go" => "go-compiler", "html" => "html-validator", "idris" => "idris2", "java" => "javac",
        "javascript" => "nodejs", "kotlin" => "kotlin-compiler", "move" => "move-compiler", "nim" => "nim", "opencl" => "opencl-runtime", "purescript" => "purescript",
        "python" => "cpython", "r" => "r-runtime", "racket" => "racket", "rocm-hip" => "hip-runtime", "rust" => "rustc", "scheme" => "scheme-runtime",
        "sql" => "sqlite", "swift" => "swiftc", "typescript" => "tsc", "unlambda" => "unlambda-interpreter", "vulkan" => "vulkan-runtime", "vyper" => "vyper", "whitespace" => "whitespace-interpreter",
        _ => "custom-tool",
        },
    }
}

fn slug(value: &str) -> String {
    let mut result = String::new();
    let mut prior_separator = false;
    for character in value.chars() {
        if character.is_ascii_alphanumeric() { result.push(character.to_ascii_lowercase()); prior_separator = false; }
        else if !prior_separator { result.push('-'); prior_separator = true; }
    }
    result.trim_matches('-').to_string()
}

fn normalized_severity(severity: &str) -> &'static str {
    match severity {
        "Fatal" => "fatal", "Warning" => "warning", "Linter Rule" => "information", "Undefined Behavior" | "Runtime Exception" | "Compiler Error" => "error",
        _ => "information",
    }
}

fn classifications_for(category: &str, severity: &str) -> Vec<String> {
    let category = category.to_ascii_lowercase();
    let primary = if category.contains("syntax") { "syntax-error" }
        else if category.contains("type") { "type-error" }
        else if category.contains("memory") { "memory-error" }
        else if category.contains("concurrency") { "concurrency-error" }
        else if category.contains("link") { "linker-error" }
        else if category.contains("module") { "module-error" }
        else if category.contains("import") { "import-error" }
        else if category.contains("runtime") { "runtime-error" }
        else if category.contains("security") { "security-error" }
        else if category.contains("network") { "network-error" }
        else if category.contains("database") { "database-error" }
        else if category.contains("io") { "io-error" }
        else { "compilation-error" };
    let mut values = vec![primary.to_string()];
    if severity == "Runtime Exception" { values.push("exception".to_string()); }
    if severity == "Warning" { values.push("warning".to_string()); }
    if severity == "Linter Rule" { values.push("linter-diagnostic".to_string()); }
    values
}

fn concept_ids_for(entry: &ErrorEntry, classifications: &[String]) -> Vec<&'static str> {
    let title = format!("{} {} {}", entry.code, entry.title, entry.description).to_ascii_lowercase();
    let mut concepts = Vec::new();
    if title.contains("moved value") || title.contains("borrow") { concepts.push("borrow-violation"); }
    if title.contains("null") || title.contains("undefined") { concepts.push("null-access"); }
    if title.contains("not assignable") || title.contains("implicitly convert") || title.contains("type mismatch") { concepts.push("type-mismatch"); }
    if title.contains("not found") || title.contains("undeclared") || title.contains("cannot find name") { concepts.push("undefined-identifier"); }
    if title.contains("module") || title.contains("import") || title.contains("assembly reference") { concepts.push("missing-module"); }
    if title.contains("deadlock") { concepts.push("deadlock"); }
    if title.contains("duplicate") { concepts.push("duplicate-declaration"); }
    if classifications.iter().any(|value| value == "syntax-error") { concepts.push("invalid-syntax"); }
    concepts.sort_unstable(); concepts.dedup(); concepts
}

fn fingerprint(value: &str) -> String {
    let mut result = String::new();
    let mut in_quote = false;
    let mut inserted_variable = false;
    for character in value.to_ascii_lowercase().chars().take(512) {
        if character == '\'' || character == '"' || character == '`' {
            in_quote = !in_quote;
            if in_quote && !inserted_variable { result.push_str("{value}"); inserted_variable = true; }
            continue;
        }
        if in_quote { continue; }
        if character.is_ascii_digit() { if !result.ends_with("{n}") { result.push_str("{n}"); } continue; }
        if character.is_whitespace() { if !result.ends_with(' ') { result.push(' '); } } else { result.push(character); }
    }
    result.trim().to_string()
}

fn initialize_knowledge_graph(connection: &Connection) -> Result<(), String> {
    let languages: Vec<KnowledgeLanguage> = serde_json::from_str(LANGUAGE_DATA).map_err(|error| format!("Invalid language profiles: {error}"))?;
    let tools: Vec<KnowledgeTool> = serde_json::from_str(TOOL_DATA).map_err(|error| format!("Invalid tool profiles: {error}"))?;
    let concepts: Vec<KnowledgeConcept> = serde_json::from_str(CONCEPT_DATA).map_err(|error| format!("Invalid concepts: {error}"))?;
    let causes: Vec<RootCause> = serde_json::from_str(ROOT_CAUSE_DATA).map_err(|error| format!("Invalid root causes: {error}"))?;
    for language in languages { connection.execute("INSERT INTO languages (id, name, ecosystem, status) VALUES (?1, ?2, ?3, ?4) ON CONFLICT(id) DO UPDATE SET name=excluded.name, ecosystem=excluded.ecosystem, status=excluded.status", params![language.id, language.name, language.ecosystem, language.status]).map_err(|error| error.to_string())?; }
    for tool in tools { connection.execute("INSERT INTO tools (id, language_id, name, kind) VALUES (?1, ?2, ?3, ?4) ON CONFLICT(id) DO UPDATE SET language_id=excluded.language_id, name=excluded.name, kind=excluded.kind", params![tool.id, tool.language_id, tool.name, tool.kind]).map_err(|error| error.to_string())?; }
    for concept in concepts { connection.execute("INSERT INTO concepts (id, name, classification, description) VALUES (?1, ?2, ?3, ?4) ON CONFLICT(id) DO UPDATE SET name=excluded.name, classification=excluded.classification, description=excluded.description", params![concept.id, concept.name, concept.classification, concept.description]).map_err(|error| error.to_string())?; }
    for cause in causes { connection.execute("INSERT INTO root_causes (id, name) VALUES (?1, ?2) ON CONFLICT(id) DO UPDATE SET name=excluded.name", params![cause.id, cause.name]).map_err(|error| error.to_string())?; }

    let records = {
        let mut statement = connection.prepare("SELECT id, language, code, category, severity, title, description, bad_example, good_example, version_introduced, version_deprecated, source_url, tier, frequency, situational_context, interaction_types, related_errors, state_snapshot FROM entries").map_err(|error| error.to_string())?;
        let rows = statement.query_map([], |row| Ok(ErrorEntry { id: row.get(0)?, language: row.get(1)?, code: row.get(2)?, category: row.get(3)?, severity: row.get(4)?, title: row.get(5)?, description: row.get(6)?, bad_example: row.get(7)?, good_example: row.get(8)?, version_introduced: row.get(9)?, version_deprecated: row.get(10)?, source_url: row.get(11)?, tier: row.get(12)?, frequency: row.get(13)?, situational_context: serde_json::from_str(&row.get::<_, String>(14)?).unwrap_or_default(), interaction_types: serde_json::from_str(&row.get::<_, String>(15)?).unwrap_or_default(), related_errors: serde_json::from_str(&row.get::<_, String>(16)?).unwrap_or_default(), state_snapshot: row.get::<_, Option<String>>(17)?.and_then(|value| serde_json::from_str(&value).ok()), score: None })) .map_err(|error| error.to_string())?;
        rows.collect::<Result<Vec<_>, _>>().map_err(|error| error.to_string())?
    };
    for record in &records { ensure_entry_metadata(connection, record)?; }
    for record in &records {
        for related in &record.related_errors {
            connection.execute("INSERT OR IGNORE INTO error_relationships (source_entry_id, target_entry_id, relationship_type) SELECT ?1, id, 'related_to' FROM entries WHERE id = ?2", params![record.id, related]).map_err(|error| error.to_string())?;
        }
    }
    Ok(())
}

fn ensure_entry_metadata(connection: &Connection, entry: &ErrorEntry) -> Result<(), String> {
    let language_id = normalized_language_id(&entry.language);
    connection.execute("INSERT OR IGNORE INTO languages (id, name, ecosystem, status) VALUES (?1, ?2, 'Imported/custom language', 'custom')", params![language_id, entry.language]).map_err(|error| error.to_string())?;
    let tool_id = default_tool_for(entry, &language_id).to_string();
    connection.execute("INSERT OR IGNORE INTO tools (id, language_id, name, kind) VALUES (?1, ?2, ?3, 'toolchain')", params![tool_id, language_id, format!("{} toolchain", entry.language)]).map_err(|error| error.to_string())?;
    let classifications = classifications_for(&entry.category, &entry.severity);
    let concepts = concept_ids_for(entry, &classifications);
    let causes: Vec<serde_json::Value> = concepts.iter().filter_map(|concept| match *concept {
        "undefined-identifier" => Some(serde_json::json!({"id":"incorrect-scope","likelihood":"common"})),
        "type-mismatch" => Some(serde_json::json!({"id":"invalid-type","likelihood":"common"})),
        "missing-module" => Some(serde_json::json!({"id":"missing-dependency","likelihood":"common"})),
        "invalid-syntax" => Some(serde_json::json!({"id":"invalid-syntax","likelihood":"common"})),
        _ => None,
    }).collect();
    let generated = entry.title == "Needs editorial enrichment" || entry.bad_example.contains("Add a minimal reproduction") || entry.bad_example.contains("Registry-only record");
    let canonical_message = if entry.code.chars().any(|character| character.is_whitespace()) { entry.title.clone() } else { format!("{}: {}", entry.code, entry.title) };
    let canonical_id = format!("{}.{}.{}", language_id, tool_id, slug(&entry.code));
    let provenance = serde_json::json!({"source_type": if generated { "official-registry-metadata" } else { "curated-entry" }, "source_authority": if generated { "Official" } else { "Contributor reviewed" }, "review_state": if generated { "generated-draft" } else { "reviewed" }, "source_url": entry.source_url, "source_title": entry.title, "dataset_version": "2026.08"});
    connection.execute(
        "INSERT OR IGNORE INTO error_metadata (entry_id, canonical_id, language_id, tool_id, classifications, normalized_severity, canonical_message, summary, when_it_occurs, causes, fixes, prevention, explanation_of_example, tags, aliases, fingerprint, signature_kind, signature_pattern, platforms, provenance, verification_status, updated_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, '[]', NULL, NULL, ?11, ?12, ?13, 'identifier', NULL, '[]', ?14, ?15, '2026-08-27')",
        params![entry.id, canonical_id, language_id, tool_id, serde_json::to_string(&classifications).map_err(|error| error.to_string())?, normalized_severity(&entry.severity), canonical_message, entry.description, serde_json::to_string(&entry.situational_context).map_err(|error| error.to_string())?, serde_json::to_string(&causes).map_err(|error| error.to_string())?, serde_json::to_string(&vec![entry.category.clone(), entry.severity.clone()]).map_err(|error| error.to_string())?, serde_json::to_string(&vec![entry.code.clone(), entry.title.clone()]).map_err(|error| error.to_string())?, fingerprint(&entry.title), serde_json::to_string(&provenance).map_err(|error| error.to_string())?, if generated { "Needs Review" } else { "Verified" }]
    ).map_err(|error| error.to_string())?;
    for concept in concepts { connection.execute("INSERT OR IGNORE INTO error_concepts (entry_id, concept_id) VALUES (?1, ?2)", params![entry.id, concept]).map_err(|error| error.to_string())?; }
    Ok(())
}

fn validate_entry(entry: &ErrorEntry) -> Result<(), String> {
    let valid_severities = ["Compiler Error", "Warning", "Runtime Exception", "Linter Rule", "Fatal", "Undefined Behavior"];
    if entry.id.len() < 3 || !entry.id.chars().all(|character| character.is_ascii_lowercase() || character.is_ascii_digit() || character == '_') || !entry.id.contains('_') {
        return Err(format!("Entry '{}' has an invalid id; use lowercase segments separated by underscores", entry.id));
    }
    if [entry.language.as_str(), entry.code.as_str(), entry.category.as_str(), entry.title.as_str(), entry.description.as_str(), entry.bad_example.as_str(), entry.good_example.as_str()].iter().any(|value| value.trim().is_empty()) {
        return Err(format!("Entry '{}' has a required blank field", entry.id));
    }
    if !valid_severities.contains(&entry.severity.as_str()) {
        return Err(format!("Entry '{}' has unsupported severity '{}'", entry.id, entry.severity));
    }
    if !(1..=4).contains(&entry.tier) { return Err(format!("Entry '{}' must use a tier from 1 to 4", entry.id)); }
    if !["Common", "Uncommon", "Rare", "Situational"].contains(&entry.frequency.as_str()) { return Err(format!("Entry '{}' has unsupported frequency '{}'", entry.id, entry.frequency)); }
    if let Some(url) = &entry.source_url { if !(url.starts_with("https://") || url.starts_with("http://")) { return Err(format!("Entry '{}' has an invalid source_url", entry.id)); } }
    Ok(())
}

fn upsert_entry(connection: &Connection, entry: &ErrorEntry) -> Result<(), String> {
    connection.execute(
        "INSERT INTO entries (id, language, code, category, severity, title, description, bad_example, good_example, version_introduced, version_deprecated, source_url, tier, frequency, situational_context, interaction_types, related_errors, state_snapshot)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, ?18)
         ON CONFLICT(id) DO UPDATE SET language=excluded.language, code=excluded.code, category=excluded.category, severity=excluded.severity, title=excluded.title, description=excluded.description, bad_example=excluded.bad_example, good_example=excluded.good_example, version_introduced=excluded.version_introduced, version_deprecated=excluded.version_deprecated, source_url=excluded.source_url, tier=excluded.tier, frequency=excluded.frequency, situational_context=excluded.situational_context, interaction_types=excluded.interaction_types, related_errors=excluded.related_errors, state_snapshot=excluded.state_snapshot",
        params![entry.id, entry.language, entry.code, entry.category, entry.severity, entry.title, entry.description, entry.bad_example, entry.good_example, entry.version_introduced, entry.version_deprecated, entry.source_url, entry.tier, entry.frequency, serde_json::to_string(&entry.situational_context).map_err(|error| error.to_string())?, serde_json::to_string(&entry.interaction_types).map_err(|error| error.to_string())?, serde_json::to_string(&entry.related_errors).map_err(|error| error.to_string())?, entry.state_snapshot.as_ref().map(serde_json::to_string).transpose().map_err(|error| error.to_string())?]
    ).map_err(|error| error.to_string())?;
    Ok(())
}

fn fts_query(query: &str) -> String {
    query.split(|character: char| !character.is_alphanumeric()).filter(|word| !word.is_empty()).map(|word| format!("{}*", word)).collect::<Vec<_>>().join(" AND ")
}

fn metadata_from_row(row: &rusqlite::Row<'_>) -> Result<ErrorMetadata, rusqlite::Error> {
    Ok(ErrorMetadata {
        entry_id: row.get(0)?, canonical_id: row.get(1)?, language_id: row.get(2)?, tool_id: row.get(3)?,
        classifications: serde_json::from_str(&row.get::<_, String>(4)?).unwrap_or_default(), normalized_severity: row.get(5)?, canonical_message: row.get(6)?,
        summary: row.get(7)?, when_it_occurs: serde_json::from_str(&row.get::<_, String>(8)?).unwrap_or_default(), causes: serde_json::from_str(&row.get::<_, String>(9)?).unwrap_or_default(),
        fixes: serde_json::from_str(&row.get::<_, String>(10)?).unwrap_or_default(), prevention: row.get(11)?, explanation_of_example: row.get(12)?,
        tags: serde_json::from_str(&row.get::<_, String>(13)?).unwrap_or_default(), aliases: serde_json::from_str(&row.get::<_, String>(14)?).unwrap_or_default(), fingerprint: row.get(15)?, signature_kind: row.get(16)?,
        signature_pattern: row.get(17)?, platforms: serde_json::from_str(&row.get::<_, String>(18)?).unwrap_or_default(), provenance: serde_json::from_str(&row.get::<_, String>(19)?).unwrap_or(serde_json::Value::Null),
        verification_status: row.get(20)?, updated_at: row.get(21)?,
    })
}

fn metadata_select() -> &'static str {
    "SELECT entry_id, canonical_id, language_id, tool_id, classifications, normalized_severity, canonical_message, summary, when_it_occurs, causes, fixes, prevention, explanation_of_example, tags, aliases, fingerprint, signature_kind, signature_pattern, platforms, provenance, verification_status, updated_at FROM error_metadata"
}

fn coverage_percentage(numerator: i64, denominator: i64) -> f64 {
    if denominator == 0 { 0.0 } else { ((numerator * 1000 / denominator) as f64) / 10.0 }
}

fn coverage_tier(records: i64, target: i64, quality: &CoverageQuality) -> &'static str {
    if records == 0 { "Experimental" }
    else if target > 0 && records >= target && quality.verified >= 95.0 && quality.explanations >= 95.0 && quality.examples >= 60.0 && quality.fixes >= 70.0 && quality.sources >= 95.0 { "Comprehensive" }
    else if target > 0 && records * 2 >= target && quality.verified >= 70.0 && quality.explanations >= 70.0 && quality.sources >= 95.0 { "Broad" }
    else if records >= 50 && quality.sources >= 95.0 { "Developing" }
    else { "Experimental" }
}

#[tauri::command]
fn get_coverage(state: State<'_, Database>) -> Result<Vec<CoverageProfile>, String> {
    let targets: Vec<CoverageTarget> = serde_json::from_str(COVERAGE_TARGET_DATA).map_err(|error| format!("Invalid coverage target data: {error}"))?;
    let target_lookup = targets.into_iter().map(|target| (target.language_id, target.target)).collect::<std::collections::HashMap<_, _>>();
    let connection = state.0.lock().map_err(|_| "Search index lock was poisoned".to_string())?;
    let mut statement = connection.prepare("SELECT l.id, l.name, COUNT(m.entry_id), COUNT(DISTINCT m.tool_id), SUM(CASE WHEN m.verification_status IN ('Official', 'Verified', 'Community Verified') THEN 1 ELSE 0 END), SUM(CASE WHEN m.verification_status IN ('Official', 'Verified', 'Community Verified') AND e.bad_example NOT LIKE '%Add a minimal reproduction%' AND e.bad_example NOT LIKE '%Registry-only record%' THEN 1 ELSE 0 END), SUM(CASE WHEN m.verification_status IN ('Official', 'Verified', 'Community Verified') AND e.good_example NOT LIKE '%Add a reviewed repair%' AND e.good_example NOT LIKE '%Registry-only record%' AND e.good_example NOT LIKE '%corresponding repair%' THEN 1 ELSE 0 END), SUM(CASE WHEN e.source_url IS NOT NULL THEN 1 ELSE 0 END), SUM(CASE WHEN e.version_introduced IS NOT NULL OR e.version_deprecated IS NOT NULL THEN 1 ELSE 0 END), (SELECT COUNT(DISTINCT r.source_entry_id) FROM error_relationships r JOIN error_metadata related ON related.entry_id=r.source_entry_id WHERE related.language_id=l.id) FROM languages l LEFT JOIN error_metadata m ON m.language_id=l.id LEFT JOIN entries e ON e.id=m.entry_id GROUP BY l.id, l.name ORDER BY l.name").map_err(|error| error.to_string())?;
    let rows = statement.query_map([], |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?, row.get::<_, i64>(2)?, row.get::<_, i64>(3)?, row.get::<_, Option<i64>>(4)?.unwrap_or(0), row.get::<_, Option<i64>>(5)?.unwrap_or(0), row.get::<_, Option<i64>>(6)?.unwrap_or(0), row.get::<_, Option<i64>>(7)?.unwrap_or(0), row.get::<_, Option<i64>>(8)?.unwrap_or(0), row.get::<_, i64>(9)?))).map_err(|error| error.to_string())?;
    let mut profiles = Vec::new();
    for row in rows {
        let (language_id, language, records, tools, verified, examples, fixes, sources, versions, relationships) = row.map_err(|error| error.to_string())?;
        let quality = CoverageQuality { verified: coverage_percentage(verified, records), explanations: coverage_percentage(verified, records), examples: coverage_percentage(examples, records), fixes: coverage_percentage(fixes, records), sources: coverage_percentage(sources, records), versions: coverage_percentage(versions, records), relationships: coverage_percentage(relationships, records) };
        let target = *target_lookup.get(&language_id).unwrap_or(&0);
        profiles.push(CoverageProfile { language_id, language, records, target, progress: coverage_percentage(records, target), tools, tier: coverage_tier(records, target, &quality).to_string(), quality });
    }
    Ok(profiles)
}

#[tauri::command]
fn get_error_metadata(state: State<'_, Database>, entry_id: String) -> Result<ErrorMetadata, String> {
    let connection = state.0.lock().map_err(|_| "Search index lock was poisoned".to_string())?;
    connection.query_row(&format!("{} WHERE entry_id = ?1", metadata_select()), params![entry_id], metadata_from_row).optional().map_err(|error| error.to_string())?.ok_or_else(|| "Error metadata was not found".to_string())
}

fn load_entry_insights(connection: &Connection, entry_id: &str) -> Result<EntryInsights, String> {
    let (language, category, related_json): (String, String, String) = connection.query_row(
        "SELECT language, category, related_errors FROM entries WHERE id = ?1",
        params![entry_id],
        |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
    ).optional().map_err(|error| error.to_string())?.ok_or_else(|| "Diagnostic was not found".to_string())?;

    let language_total = connection.query_row(
        "SELECT COUNT(*) FROM entries WHERE language = ?1", params![language], |row| row.get(0),
    ).map_err(|error| error.to_string())?;
    let category_total = connection.query_row(
        "SELECT COUNT(*) FROM entries WHERE language = ?1 AND category = ?2", params![language, category], |row| row.get(0),
    ).map_err(|error| error.to_string())?;

    let mut frequency_counts = std::collections::HashMap::new();
    let mut frequency_statement = connection.prepare(
        "SELECT frequency, COUNT(*) FROM entries WHERE language = ?1 GROUP BY frequency",
    ).map_err(|error| error.to_string())?;
    let frequency_rows = frequency_statement.query_map(params![language], |row| {
        Ok((row.get::<_, String>(0)?, row.get::<_, i64>(1)?))
    }).map_err(|error| error.to_string())?;
    for row in frequency_rows {
        let (label, count) = row.map_err(|error| error.to_string())?;
        frequency_counts.insert(label, count);
    }
    let frequency_distribution = ["Common", "Uncommon", "Rare", "Situational"].into_iter()
        .map(|label| CountBucket { label: label.to_string(), count: *frequency_counts.get(label).unwrap_or(&0) })
        .collect();

    let mut category_statement = connection.prepare(
        "SELECT category, COUNT(*) AS total FROM entries WHERE language = ?1 GROUP BY category ORDER BY total DESC, category LIMIT 8",
    ).map_err(|error| error.to_string())?;
    let category_distribution = category_statement.query_map(params![language], |row| {
        Ok(CountBucket { label: row.get(0)?, count: row.get(1)? })
    }).map_err(|error| error.to_string())?.collect::<Result<Vec<_>, _>>().map_err(|error| error.to_string())?;

    let related_ids: Vec<String> = serde_json::from_str(&related_json).unwrap_or_default();
    let mut related_entries = Vec::new();
    let mut related_statement = connection.prepare(
        "SELECT id, language, code, title, category, severity, frequency FROM entries WHERE id = ?1",
    ).map_err(|error| error.to_string())?;
    for related_id in related_ids.into_iter().take(8) {
        if let Some(entry) = related_statement.query_row(params![related_id], |row| Ok(RelatedEntry {
            id: row.get(0)?, language: row.get(1)?, code: row.get(2)?, title: row.get(3)?,
            category: row.get(4)?, severity: row.get(5)?, frequency: row.get(6)?,
        })).optional().map_err(|error| error.to_string())? {
            related_entries.push(entry);
        }
    }

    Ok(EntryInsights { language_total, category_total, frequency_distribution, category_distribution, related_entries })
}

#[tauri::command]
fn get_entry_insights(state: State<'_, Database>, entry_id: String) -> Result<EntryInsights, String> {
    let connection = state.0.lock().map_err(|_| "Search index lock was poisoned".to_string())?;
    load_entry_insights(&connection, &entry_id)
}

#[tauri::command]
fn get_languages(state: State<'_, Database>) -> Result<Vec<LanguageProfile>, String> {
    let connection = state.0.lock().map_err(|_| "Search index lock was poisoned".to_string())?;
    let mut statement = connection.prepare("SELECT l.id, l.name, l.ecosystem, l.status, COUNT(m.entry_id), COUNT(DISTINCT t.id) FROM languages l LEFT JOIN error_metadata m ON m.language_id = l.id LEFT JOIN tools t ON t.language_id = l.id GROUP BY l.id, l.name, l.ecosystem, l.status ORDER BY COUNT(m.entry_id) DESC, l.name").map_err(|error| error.to_string())?;
    let rows = statement.query_map([], |row| Ok(LanguageProfile { id: row.get(0)?, name: row.get(1)?, ecosystem: row.get(2)?, status: row.get(3)?, diagnostic_count: row.get(4)?, tool_count: row.get(5)? })).map_err(|error| error.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|error| error.to_string())
}

#[tauri::command]
fn get_tools(state: State<'_, Database>) -> Result<Vec<ToolProfile>, String> {
    let connection = state.0.lock().map_err(|_| "Search index lock was poisoned".to_string())?;
    let mut statement = connection.prepare("SELECT t.id, t.language_id, t.name, t.kind, COUNT(m.entry_id) FROM tools t LEFT JOIN error_metadata m ON m.tool_id = t.id GROUP BY t.id, t.language_id, t.name, t.kind ORDER BY COUNT(m.entry_id) DESC, t.name").map_err(|error| error.to_string())?;
    let rows = statement.query_map([], |row| Ok(ToolProfile { id: row.get(0)?, language_id: row.get(1)?, name: row.get(2)?, kind: row.get(3)?, diagnostic_count: row.get(4)? })).map_err(|error| error.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|error| error.to_string())
}

#[tauri::command]
fn get_concepts(state: State<'_, Database>) -> Result<Vec<ConceptProfile>, String> {
    let connection = state.0.lock().map_err(|_| "Search index lock was poisoned".to_string())?;
    let mut statement = connection.prepare("SELECT c.id, c.name, c.classification, c.description, COUNT(ec.entry_id) FROM concepts c LEFT JOIN error_concepts ec ON ec.concept_id = c.id GROUP BY c.id, c.name, c.classification, c.description ORDER BY COUNT(ec.entry_id) DESC, c.name").map_err(|error| error.to_string())?;
    let rows = statement.query_map([], |row| Ok(ConceptProfile { id: row.get(0)?, name: row.get(1)?, classification: row.get(2)?, description: row.get(3)?, diagnostic_count: row.get(4)? })).map_err(|error| error.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|error| error.to_string())
}

fn sanitize_pasted_error(message: &str) -> Result<(String, bool), String> {
    if message.as_bytes().len() > MAX_PASTED_ERROR_BYTES { return Err(format!("Paste is too large; limit error text to {MAX_PASTED_ERROR_BYTES} bytes")); }
    let mut redacted = false;
    let mut retained = Vec::new();
    for raw_line in message.replace("\r\n", "\n").lines().rev().take(80).collect::<Vec<_>>().into_iter().rev() {
        let lower = raw_line.to_ascii_lowercase();
        if ["api_key", "apikey", "authorization:", "password=", "token=", "secret="].iter().any(|marker| lower.contains(marker)) {
            retained.push("[redacted secret-bearing line]".to_string()); redacted = true; continue;
        }
        let trimmed = raw_line.trim();
        if trimmed.starts_with("C:\\") || trimmed.starts_with("/home/") || trimmed.starts_with("/users/") || trimmed.starts_with("/private/") {
            retained.push("[redacted local path]".to_string()); redacted = true; continue;
        }
        if trimmed.contains("://") && trimmed.contains('@') {
            retained.push("[redacted credential-bearing URL]".to_string()); redacted = true; continue;
        }
        retained.push(trimmed.to_string());
    }
    let normalized = retained.into_iter().filter(|line| !line.is_empty()).collect::<Vec<_>>().join("\n");
    Ok((normalized, redacted))
}

fn likely_language(message: &str) -> Option<&'static str> {
    let message = message.to_ascii_lowercase();
    if message.contains("error[") || message.contains("rustc") { Some("Rust") }
    else if message.contains("ts") && message.contains("error") { Some("TypeScript") }
    else if message.contains("cs") && message.contains("error") { Some("C#") }
    else if message.contains("traceback") || message.contains("nameerror") { Some("Python") }
    else if message.contains("panic:") || message.contains("goroutine") { Some("Go") }
    else if message.contains("exception in thread") { Some("Java") }
    else { None }
}

#[tauri::command]
fn detect_error(state: State<'_, Database>, message: String) -> Result<DetectionResult, String> {
    let (normalized_message, redacted) = sanitize_pasted_error(&message)?;
    let language_hint = likely_language(&normalized_message);
    let mut identifiers: Vec<String> = normalized_message.split(|character: char| !character.is_ascii_alphanumeric() && character != '_').filter(|value| value.len() >= 3).map(str::to_owned).collect();
    identifiers.sort(); identifiers.dedup(); identifiers.truncate(64);
    let connection = state.0.lock().map_err(|_| "Search index lock was poisoned".to_string())?;
    let mut matches = Vec::new();
    for identifier in identifiers {
        let mut statement = connection.prepare("SELECT e.id, m.canonical_id, e.language, m.tool_id, e.code FROM entries e JOIN error_metadata m ON m.entry_id=e.id WHERE lower(e.code)=lower(?1) OR lower(e.title)=lower(?1) LIMIT 8").map_err(|error| error.to_string())?;
        let rows = statement.query_map(params![identifier], |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?, row.get::<_, String>(2)?, row.get::<_, String>(3)?, row.get::<_, String>(4)?))).map_err(|error| error.to_string())?;
        for row in rows {
            let (entry_id, canonical_id, language, tool_id, code) = row.map_err(|error| error.to_string())?;
            if let Some(hint) = language_hint { if language != hint { continue; } }
            if matches.iter().any(|candidate: &DetectionMatch| candidate.entry_id == entry_id) { continue; }
            let code_match = code.eq_ignore_ascii_case(&identifier);
            matches.push(DetectionMatch { entry_id, canonical_id, language, tool_id, code, confidence: if code_match { 0.99 } else { 0.86 }, confidence_label: if code_match { "Exact Match".to_string() } else { "Likely Match".to_string() } });
        }
    }
    matches.sort_by(|left, right| right.confidence.total_cmp(&left.confidence)); matches.truncate(5);
    Ok(DetectionResult { normalized_message, matches, redacted })
}

#[tauri::command]
fn search_entries(state: State<'_, Database>, query: String, filters: Filters) -> Result<Vec<ErrorEntry>, String> {
    let connection = state.0.lock().map_err(|_| "Search index lock was poisoned".to_string())?;
    let mut clauses = Vec::new();
    let mut values: Vec<rusqlite::types::Value> = Vec::new();
    let mut using_fts = false;
    if !query.trim().is_empty() {
        let prepared = fts_query(&query);
        if !prepared.is_empty() { clauses.push("entries_fts MATCH ?".to_string()); values.push(prepared.into()); using_fts = true; }
    }
    for (column, selected) in [("language", &filters.languages), ("category", &filters.categories), ("severity", &filters.severities), ("frequency", &filters.frequencies)] {
        if !selected.is_empty() {
            let marks = std::iter::repeat("?").take(selected.len()).collect::<Vec<_>>().join(", ");
            clauses.push(format!("entries.{column} IN ({marks})"));
            values.extend(selected.iter().cloned().map(Into::into));
        }
    }
    if !filters.interactions.is_empty() {
        let marks = std::iter::repeat("?").take(filters.interactions.len()).collect::<Vec<_>>().join(", ");
        clauses.push(format!("EXISTS (SELECT 1 FROM json_each(entries.interaction_types) WHERE value IN ({marks}))"));
        values.extend(filters.interactions.iter().cloned().map(Into::into));
    }
    let where_clause = if clauses.is_empty() { String::new() } else { format!("WHERE {}", clauses.join(" AND ")) };
    let query_sql = if using_fts {
        format!("SELECT entries.id, entries.language, entries.code, entries.category, entries.severity, entries.title, entries.description, entries.bad_example, entries.good_example, entries.version_introduced, entries.version_deprecated, entries.source_url, entries.tier, entries.frequency, entries.situational_context, entries.interaction_types, entries.related_errors, entries.state_snapshot, bm25(entries_fts, 10.0, 6.0, 1.0, 3.0, 2.0) AS score FROM entries JOIN entries_fts ON entries.rowid = entries_fts.rowid {where_clause} ORDER BY score, entries.code LIMIT {MAX_RESULTS}")
    } else {
        format!("SELECT entries.id, entries.language, entries.code, entries.category, entries.severity, entries.title, entries.description, entries.bad_example, entries.good_example, entries.version_introduced, entries.version_deprecated, entries.source_url, entries.tier, entries.frequency, entries.situational_context, entries.interaction_types, entries.related_errors, entries.state_snapshot, 0.0 AS score FROM entries {where_clause} ORDER BY entries.language, entries.code LIMIT {MAX_RESULTS}")
    };
    let mut statement = connection.prepare(&query_sql).map_err(|error| format!("Search query failed: {error}"))?;
    let rows = statement.query_map(params_from_iter(values), |row| Ok(ErrorEntry {
        id: row.get(0)?, language: row.get(1)?, code: row.get(2)?, category: row.get(3)?, severity: row.get(4)?, title: row.get(5)?, description: row.get(6)?, bad_example: row.get(7)?, good_example: row.get(8)?, version_introduced: row.get(9)?, version_deprecated: row.get(10)?, source_url: row.get(11)?, tier: row.get(12)?, frequency: row.get(13)?, situational_context: serde_json::from_str(&row.get::<_, String>(14)?).unwrap_or_default(), interaction_types: serde_json::from_str(&row.get::<_, String>(15)?).unwrap_or_default(), related_errors: serde_json::from_str(&row.get::<_, String>(16)?).unwrap_or_default(), state_snapshot: row.get::<_, Option<String>>(17)?.and_then(|value| serde_json::from_str(&value).ok()), score: Some(row.get(18)?),
    })).map_err(|error| error.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|error| error.to_string())
}

#[tauri::command]
fn get_matrix(state: State<'_, Database>, filters: Filters) -> Result<Vec<MatrixCell>, String> {
    let connection = state.0.lock().map_err(|_| "Search index lock was poisoned".to_string())?;
    let mut clauses = Vec::new();
    let mut values: Vec<rusqlite::types::Value> = Vec::new();
    for (column, selected) in [("language", &filters.languages), ("category", &filters.categories), ("severity", &filters.severities), ("frequency", &filters.frequencies)] {
        if !selected.is_empty() {
            let marks = std::iter::repeat("?").take(selected.len()).collect::<Vec<_>>().join(", ");
            clauses.push(format!("{column} IN ({marks})"));
            values.extend(selected.iter().cloned().map(Into::into));
        }
    }
    if !filters.interactions.is_empty() {
        let marks = std::iter::repeat("?").take(filters.interactions.len()).collect::<Vec<_>>().join(", ");
        clauses.push(format!("EXISTS (SELECT 1 FROM json_each(interaction_types) WHERE value IN ({marks}))"));
        values.extend(filters.interactions.iter().cloned().map(Into::into));
    }
    let where_clause = if clauses.is_empty() { String::new() } else { format!("WHERE {}", clauses.join(" AND ")) };
    let sql = format!("SELECT language, category, frequency, COUNT(*) FROM entries {where_clause} GROUP BY language, category, frequency ORDER BY language, category");
    let mut statement = connection.prepare(&sql).map_err(|error| error.to_string())?;
    let rows = statement.query_map(params_from_iter(values), |row| Ok(MatrixCell { language: row.get(0)?, category: row.get(1)?, frequency: row.get(2)?, count: row.get(3)? })).map_err(|error| error.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|error| error.to_string())
}

#[tauri::command]
fn get_facets(state: State<'_, Database>) -> Result<Facets, String> {
    let connection = state.0.lock().map_err(|_| "Search index lock was poisoned".to_string())?;
    let list = |column: &str| -> Result<Vec<String>, String> {
        let mut statement = connection.prepare(&format!("SELECT DISTINCT {column} FROM entries ORDER BY {column}")).map_err(|error| error.to_string())?;
        let values = statement.query_map([], |row| row.get(0)).map_err(|error| error.to_string())?.collect::<Result<Vec<String>, _>>().map_err(|error| error.to_string());
        values
    };
    let interactions = {
        let mut statement = connection.prepare("SELECT DISTINCT value FROM entries, json_each(entries.interaction_types) ORDER BY value").map_err(|error| error.to_string())?;
        let values = statement.query_map([], |row| row.get(0)).map_err(|error| error.to_string())?.collect::<Result<Vec<String>, _>>().map_err(|error| error.to_string())?;
        values
    };
    Ok(Facets { languages: list("language")?, categories: list("category")?, severities: list("severity")?, frequencies: list("frequency")?, interactions, total: connection.query_row("SELECT COUNT(*) FROM entries", [], |row| row.get(0)).map_err(|error| error.to_string())? })
}

#[tauri::command]
fn export_database(app: AppHandle, state: State<'_, Database>, destination: String) -> Result<String, String> {
    let target = PathBuf::from(&destination);
    if target.extension().is_none() { return Err("Choose a destination with a .db or .sqlite extension".to_string()); }
    let connection = state.0.lock().map_err(|_| "Database lock was poisoned".to_string())?;
    connection.execute_batch("PRAGMA wal_checkpoint(TRUNCATE);").map_err(|error| error.to_string())?;
    fs::copy(database_path(&app)?, &target).map_err(|error| format!("Backup failed: {error}"))?;
    Ok(target.display().to_string())
}

fn parse_frontmatter(input: &str) -> Result<ErrorEntry, String> {
    let normalized = input.replace("\r\n", "\n");
    let stripped = normalized.strip_prefix("---\n").ok_or("Markdown contribution must start with YAML frontmatter (---)")?;
    let (header, body) = stripped.split_once("\n---\n").ok_or("Markdown contribution frontmatter was not closed")?;
    let mut fields = std::collections::HashMap::new();
    for line in header.lines() {
        let (key, raw_value) = line.split_once(':').ok_or_else(|| format!("Invalid frontmatter line: {line}"))?;
        fields.insert(key.trim().to_owned(), raw_value.trim().trim_matches('"').to_owned());
    }
    let mut code_blocks = Vec::new();
    let mut current_block: Option<Vec<&str>> = None;
    for line in body.lines() {
        if line.trim_start().starts_with("```") {
            if let Some(lines) = current_block.take() { code_blocks.push(lines.join("\n")); } else { current_block = Some(Vec::new()); }
        } else if let Some(lines) = &mut current_block { lines.push(line); }
    }
    if current_block.is_some() { return Err("Markdown contribution has an unclosed code fence".to_string()); }
    let bad_example = code_blocks.first().ok_or("Markdown contribution needs a first fenced broken-code block")?.trim().to_owned();
    let good_example = code_blocks.get(1).ok_or("Markdown contribution needs a second fenced fixed-code block")?.trim().to_owned();
    let description = fields.remove("description").or_else(|| body.split("## Broken").next().map(str::trim).filter(|value| !value.is_empty()).map(str::to_owned)).unwrap_or_default();
    let field = |name: &str, values: &std::collections::HashMap<String, String>| values.get(name).cloned().unwrap_or_default();
    let list = |name: &str| fields.get(name).map(|value| value.split(',').map(str::trim).filter(|item| !item.is_empty()).map(str::to_owned).collect()).unwrap_or_default();
    Ok(ErrorEntry { id: field("id", &fields), language: field("language", &fields), code: field("code", &fields), category: field("category", &fields), severity: field("severity", &fields), title: field("title", &fields), description, bad_example, good_example, version_introduced: fields.get("version_introduced").cloned().filter(|value| value != "null" && !value.is_empty()), version_deprecated: fields.get("version_deprecated").cloned().filter(|value| value != "null" && !value.is_empty()), source_url: fields.get("source_url").or_else(|| fields.get("source_reference")).cloned().filter(|value| value != "null" && !value.is_empty()), tier: fields.get("tier").and_then(|value| value.parse().ok()).unwrap_or_else(default_tier), frequency: fields.get("frequency").cloned().unwrap_or_else(default_frequency), situational_context: list("situational_context"), interaction_types: list("interaction_types"), related_errors: list("related_errors"), state_snapshot: None, score: None })
}

fn load_file(path: &Path) -> Result<Vec<ErrorEntry>, String> {
    let content = fs::read_to_string(path).map_err(|error| format!("Could not read {}: {error}", path.display()))?;
    match path.extension().and_then(|extension| extension.to_str()).unwrap_or_default().to_lowercase().as_str() {
        "json" => match serde_json::from_str::<Vec<ErrorEntry>>(&content) { Ok(entries) => Ok(entries), Err(_) => serde_json::from_str::<ErrorEntry>(&content).map(|entry| vec![entry]).map_err(|error| format!("{} is not a valid entry JSON file: {error}", path.display())) },
        "md" | "markdown" | "yaml" | "yml" => parse_frontmatter(&content).map(|entry| vec![entry]),
        _ => Ok(Vec::new()),
    }
}

fn collect_contribution_files(dir: &Path, files: &mut Vec<PathBuf>) -> Result<(), String> {
    for entry in fs::read_dir(dir).map_err(|error| error.to_string())? {
        let path = entry.map_err(|error| error.to_string())?.path();
        if path.is_dir() { collect_contribution_files(&path, files)?; } else { files.push(path); }
    }
    Ok(())
}

fn import_directory(connection: &Connection, directory: &Path) -> Result<usize, String> {
    let mut files = Vec::new(); collect_contribution_files(directory, &mut files)?;
    let mut ids = HashSet::new(); let mut entries = Vec::new();
    for file in files { for entry in load_file(&file)? { validate_entry(&entry)?; if !ids.insert(entry.id.clone()) { return Err(format!("Duplicate id '{}' in import source", entry.id)); } entries.push(entry); } }
    let transaction = connection.unchecked_transaction().map_err(|error| error.to_string())?;
    for entry in &entries { upsert_entry(&transaction, entry)?; }
    transaction.commit().map_err(|error| error.to_string())?;
    for entry in &entries { ensure_entry_metadata(connection, entry)?; }
    Ok(entries.len())
}

#[tauri::command]
fn import_contributions(state: State<'_, Database>, source: String) -> Result<usize, String> {
    let source = PathBuf::from(source);
    if !source.is_dir() { return Err("Contribution source must be a directory".to_string()); }
    let connection = state.0.lock().map_err(|_| "Database lock was poisoned".to_string())?;
    import_directory(&connection, &source)
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            let handle = app.handle().clone();
            let connection = initialize_database(&database_path(&handle)?).map_err(std::io::Error::other)?;
            let default_contributions = contribution_dir(&handle).map_err(std::io::Error::other)?;
            if let Err(error) = import_directory(&connection, &default_contributions) { eprintln!("Skipping invalid local contribution: {error}"); }
            app.manage(Database(Mutex::new(connection)));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![search_entries, get_facets, get_matrix, get_error_metadata, get_entry_insights, get_languages, get_tools, get_concepts, get_coverage, detect_error, export_database, import_contributions])
        .run(tauri::generate_context!())
        .expect("error while running LexiconError");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bundled_seed_entries_are_valid() {
        let entries: Vec<ErrorEntry> = serde_json::from_str(SEED_DATA).expect("seed JSON should parse");
        assert!(entries.len() >= 14);
        for entry in entries { validate_entry(&entry).expect("seed entry should meet backend constraints"); }
    }

    #[test]
    fn bundled_review_entries_are_valid() {
        let mut count = 0;
        for source in REVIEW_DATA {
            let entries: Vec<ErrorEntry> = serde_json::from_str(source).expect("review JSON should parse");
            for entry in entries { validate_entry(&entry).expect("review entry should meet backend constraints"); count += 1; }
        }
        assert!(count >= 12_000, "expected the reviewed catalog to include the Wave A expansion");
    }

    #[test]
    fn fresh_database_merges_review_and_curated_catalogs() {
        let unique = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).expect("clock should be valid").as_nanos();
        let path = std::env::temp_dir().join(format!("lexicon-error-test-{}-{unique}.db", std::process::id()));
        let connection = initialize_database(&path).expect("fresh database should initialize");
        let count: i64 = connection.query_row("SELECT COUNT(*) FROM entries", [], |row| row.get(0)).expect("count should query");
        let reviewed_ids: HashSet<String> = REVIEW_DATA.iter().flat_map(|source| serde_json::from_str::<Vec<ErrorEntry>>(source).expect("review JSON should parse")).map(|entry| entry.id).collect();
        let seed_ids: HashSet<String> = serde_json::from_str::<Vec<ErrorEntry>>(SEED_DATA).expect("seed JSON should parse").into_iter().map(|entry| entry.id).collect();
        assert_eq!(count as usize, reviewed_ids.union(&seed_ids).count());
        let description: String = connection.query_row("SELECT description FROM entries WHERE id = 'py_keyerror'", [], |row| row.get(0)).expect("curated entry should exist");
        assert!(!description.contains("Imported from"));
        let fts_hits: i64 = connection.query_row("SELECT COUNT(*) FROM entries_fts WHERE entries_fts MATCH 'E0382*'", [], |row| row.get(0)).expect("FTS should query");
        assert_eq!(fts_hits, 1);
        drop(connection);
        let _ = fs::remove_file(&path);
        let _ = fs::remove_file(path.with_extension("db-wal"));
        let _ = fs::remove_file(path.with_extension("db-shm"));
    }

    #[test]
    fn entry_insights_use_catalog_counts_and_resolve_related_diagnostics() {
        let unique = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).expect("clock should be valid").as_nanos();
        let path = std::env::temp_dir().join(format!("lexicon-error-insights-{}-{unique}.db", std::process::id()));
        let connection = initialize_database(&path).expect("fresh database should initialize");
        let insights = load_entry_insights(&connection, "py_keyerror").expect("insights should load");
        assert!(insights.language_total > 0);
        assert!(insights.category_total > 0);
        assert_eq!(insights.frequency_distribution.len(), 4);
        assert_eq!(insights.frequency_distribution[0].label, "Common");
        assert!(insights.category_distribution.iter().any(|bucket| bucket.label == "Runtime"));
        assert!(insights.related_entries.iter().any(|entry| entry.id == "js_typeerror_undefined"));
        drop(connection);
        let _ = fs::remove_file(&path);
        let _ = fs::remove_file(path.with_extension("db-wal"));
        let _ = fs::remove_file(path.with_extension("db-shm"));
    }

    #[test]
    fn markdown_frontmatter_supports_language_annotated_fences() {
        let entry = parse_frontmatter("---\nid: ts_2322\nlanguage: TypeScript\ncode: TS2322\ncategory: Type System\nseverity: Compiler Error\ntitle: Assignment mismatch\ndescription: An incompatible value crossed a typed boundary.\nsource_reference: https://www.typescriptlang.org/docs/handbook/2/everyday-types.html\ntier: 1\nfrequency: Common\n---\n\n## Broken\n```ts\nlet n: number = \\\"one\\\";\n```\n\n## Fixed\n```ts\nlet n = Number(\\\"one\\\");\n```\n").expect("frontmatter should parse");
        assert_eq!(entry.bad_example, "let n: number = \\\"one\\\";");
        assert_eq!(entry.good_example, "let n = Number(\\\"one\\\");");
        assert_eq!(entry.source_url.as_deref(), Some("https://www.typescriptlang.org/docs/handbook/2/everyday-types.html"));
        assert_eq!(entry.tier, 1);
    }
}
