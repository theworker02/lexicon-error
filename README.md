# LexiconError

LexiconError is a desktop, offline-first reference for programming-language diagnostics: compiler codes, linter rules, runtime exceptions, and source-qualified message patterns. It uses a Tauri desktop shell, React/TypeScript UI, and local SQLite FTS5 index. Core search, detection, contributions, and backups require neither an account nor a network connection.

## Included

- A premium three-pane dark interface: hierarchical domain filters, dense diagnostic grid, tabbed root-cause/diff/context inspector, and a floating Ctrl+K/Cmd+K command palette backed by the local FTS index.
- Global FTS search, structured filters, code comparisons, state snapshots, and a frequency matrix.
- A database-driven Coverage Dashboard that keeps record count separate from verified explanations, examples, fixes, source attribution, version notes, and relationships.
- A 16,474-record manifest-built catalog. Sources include rustc, Clippy, Roslyn, CPython, TypeScript, javac, Clang, Node.js, V8, SpiderMonkey, MDN, Go, Kotlin, SQLite, R, CUDA, HIP, OpenCL, and Vulkan, plus curated and user-supplied review candidates.
- Backward-compatible entry schema plus a normalized metadata layer for canonical IDs, toolchains, concepts, root causes, fingerprints, provenance, and relationships.
- Explicit source license and attribution registry at [data/knowledge/source-manifest.json](data/knowledge/source-manifest.json), with snapshot hashes at [data/review/source-lock.json](data/review/source-lock.json).
- Local contribution import and a portable SQLite backup/export workflow.

Registry imports and source-attributed user candidates are visible as `Needs Review` until an editor supplies verified explanations, minimal reproductions, and repair guidance. Counts never turn those records into verified documentation.

## Run locally

Prerequisites: Node.js 20+, Rust stable, and the [Tauri 2 platform prerequisites](https://v2.tauri.app/start/prerequisites/).

```powershell
npm.cmd install
npm.cmd run desktop:dev
```

To package the desktop application:

```powershell
npm.cmd run desktop:build
```

The first launch creates `lexicon-error.db` in the operating system application-data folder. The packaged app does not fetch registries or send telemetry.

## Build and validate the portable catalog

The review manifest is the single ordered input list for a reproducible dataset build:

```powershell
python ingestion/build_index.py --manifest data/review/manifest.json --output artifacts/lexicon-error.db
python ingestion/test_pipeline.py --database artifacts/lexicon-error.db
```

The desktop Export Database action writes the same data as a portable SQLite backup.

## Hugging Face release package

`hf/lexiconerror-diagnostics/` is a generated Dataset repository containing the 16,474-record JSONL corpus, Dataset Card, source notices, schema, snapshot lock, and SHA-256 release manifest. `hf/lexiconerror-space/` is a compute-free static Space preview that loads an 80-record sample until its public `DATASET_URL` variable points to a published dataset JSONL file.

```powershell
python ingestion/package_hf_dataset.py
python ingestion/test_hf_package.py --package hf\lexiconerror-diagnostics --space hf\lexiconerror-space
```

See [HF publishing instructions](hf/PUBLISHING.md). The source terms are composite, so the Dataset Card uses `license: other`; review the bundled notices before making a public release.

## Local CLI

```powershell
.\lexerror.cmd --database artifacts\lexicon-error.db coverage
.\lexerror.cmd --database artifacts\lexicon-error.db detect "error[E0382]: borrow of moved value"
.\lexerror.cmd --database artifacts\lexicon-error.db release-manifest --output artifacts\dataset-manifest.json
.\lexerror.cmd --database artifacts\lexicon-error.db export --format jsonl --output artifacts\lexicon-error.jsonl
```

JSON, JSONL, and CSV exports retain stable IDs and normalized metadata. Paste detection is local-only and redacts secret-bearing lines and obvious local paths before matching.

## Ingestion sources

`ingestion/fetch_official.py` saves a selected source snapshot. Adapters under `ingestion/sources/` parse saved inputs or installed tool output; they do not run network calls during parsing. The current adapters cover compiler registries, runtime message templates, installed .NET exception types, CPython standard-library patterns, Kotlin, SQLite, R, CUDA, HIP, OpenCL, Vulkan, and MDN JavaScript error-page metadata.

Generated queues live in `data/review/`. `data/review/manifest.json` places curated seed entries first and applies `keep-first`, preserving curated IDs over review queues. The source registry includes license and redistribution guidance; MDN imports intentionally retain only page metadata, not documentation bodies.

## Organizing supplied records

The user-supplied root JSON files are retained unchanged, including the GPU batch. The organizer collapses non-material numeric variants by normalized language/code, maps legacy severity labels, rejects search-result URLs as provenance, retains all original IDs in a report, and splits source-attributed candidates from source-less staging:

```powershell
python ingestion/organize_user_records.py
python ingestion/validate_entries.py data/review/user-attributed-candidates.json
```

See [data/review/user-import-report.json](data/review/user-import-report.json) for every disposition. Only source-attributed candidates are included in the review manifest; source-less records remain staged and do not count toward coverage.

## Contributions

Local JSON and Markdown contributions use [data/error-entry.schema.json](data/error-entry.schema.json). Use `source_url` or the compatible `source_reference` alias for documentation provenance. Markdown needs YAML frontmatter and two fenced code blocks, broken then fixed. The full example is [contributions/example.md](contributions/example.md).

```powershell
python ingestion/validate_entries.py path\to\entries.json
```

Do not submit identifier-only copies such as `TypeError: foo is not callable` and `TypeError: bar is not callable`. Use one parameterized diagnostic pattern when the developer meaning is the same.

## Documentation

- [Architecture](ARCHITECTURE.md)
- [Contribution workflow](CONTRIBUTING.md)
- [Security and privacy](SECURITY.md)
- [Changelog](CHANGELOG.md)

## Current scope

The catalog has broad registry coverage for C++, TypeScript, Rust, C#, JavaScript, Java, Python, and Go, and a staged multi-ecosystem queue. It does not claim exhaustive or fully editorially verified coverage where source-backed explanations, examples, or fixes remain pending.
