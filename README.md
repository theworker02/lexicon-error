# LexiconError

<p align="center">
  <img src="assets/branding/lexiconerror-mark.svg" width="104" height="104" alt="LexiconError logo" />
</p>

<p align="center"><strong>An offline-first diagnostic atlas for programming languages, infrastructure, and GPU runtimes.</strong></p>

<p align="center">Tauri 2 | React | TypeScript | Rust | SQLite FTS5 | Python ingestion</p>

## Overview

LexiconError is a local-first desktop encyclopedia for compiler diagnostics, linter rules, runtime exceptions, configuration failures, and accelerator-runtime faults. It makes each error searchable alongside its root cause, minimum trigger, hardened repair, version context, source provenance, and conceptual equivalents in other ecosystems.

It is a reference system, not an execution environment. The application never executes the snippets it displays, collects telemetry, opens a localhost API, or uploads pasted diagnostic text.

## Product surface

| Surface | What it provides |
| --- | --- |
| Command palette | Ctrl+K / Cmd+K instant offline search across codes, names, explanations, and language metadata. |
| Diagnostic catalog | FTS-ranked compact grid with language, category, severity, frequency, and interaction filters. |
| Inspector | Root cause, bad-versus-good diff, optional state snapshot, situational context, equivalents, and official source link. |
| Context matrix | Cross-language frequency view for comparing diagnostic domains. |
| Coverage dashboard | Database-derived counts, source coverage, verification state, examples, fixes, and release tier. |
| Local contributions | Validated JSON or Markdown/YAML frontmatter imports from a user-selected directory. |
| Backups and exports | Portable SQLite backup plus JSONL, JSON, CSV, coverage, and release-manifest exports. |

## Diagnostic contract

Every renderer entry has this stable core:

~~~
id, language, code, category, severity, title, description,
bad_example, good_example, version_introduced, version_deprecated,
source_url/source_reference, tier, frequency, situational_context,
interaction_types, related_errors, state_snapshot
~~~

The normalized knowledge layer adds tool identity, canonical identifier, classifications, fingerprint, provenance, and verification state. Source_reference is a supported input alias and is normalized to source_url. The exact contribution schema is [data/error-entry.schema.json](data/error-entry.schema.json).

## Four-tier taxonomy

| Tier | Scope | Examples |
| --- | --- | --- |
| 1 | Surface and syntax | Delimiters, indentation, parser failures, basic type mismatches. |
| 2 | Logic and runtime | Null dereference, bounds checks, promise failures, argument validation. |
| 3 | Compiler, linker, and static analysis | Type resolution, missing symbols, lint rules, ABI, and build diagnostics. |
| 4 | Situational systems behavior | Undefined behavior, deadlocks, allocator/device failures, and architecture-specific faults. |

Frequency and severity remain independent: a rare device fault can be critical, while a common lint rule may be low impact.

## Current catalog

The 2026.08 catalog contains **16,474 records** across **44 languages** and **45 tools**.

Core coverage includes Python, JavaScript, TypeScript, C#, Java, C, C++, Go, Rust, Zig, Kotlin, Swift, Dart, PHP, Ruby, Elixir, Scala, Clojure, R, Lua, Bash, SQL, JSON, YAML, and related ecosystems.

The registry and runtime pipeline includes rustc and Clippy, Roslyn and .NET runtime, CPython, TypeScript, javac, Clang, Node.js, V8, SpiderMonkey, Go, Kotlin, SQLite, and R. Infrastructure and accelerator coverage includes Docker, Kubernetes, Terraform, PostgreSQL, MongoDB, Redis, GraphQL, CUDA, ROCm/HIP, Vulkan, and OpenCL where curated or staged.

Generated registry records remain **Needs Review** until an editor supplies source-backed explanation, reproducible trigger, repair guidance, and version context. Record volume never implies editorial verification.

## Architecture

~~~
React + TypeScript desktop UI
        | validated Tauri IPC
Rust local application core
        |
SQLite + FTS5 entries and knowledge metadata
        |
Python source adapters -> normalization -> validation -> release index
~~~

The desktop application has no HTTP listener. Renderer calls are explicit, validated IPC commands; imported contribution files pass schema and backend validation before insertion.

## Repository layout

~~~
assets/branding/    Original reusable LexiconError SVG mark
src/                React desktop interface
src-tauri/          Rust commands, SQLite setup, Tauri configuration
data/               Curated seed, review queues, schemas, knowledge profiles
ingestion/          Parsers, organizers, validators, release/export scripts
contributions/      Example local contribution files
artifacts/          Generated release indexes, ignored by Git
hf/                 Dataset and static Space publication packages
.github/            Funding, community, issue, PR, and validation configuration
~~~

## Local development

### Prerequisites

- Node.js 20 or newer
- Rust stable
- Python 3.11 or newer
- Tauri 2 prerequisites for the target platform

### Install and run

~~~powershell
npm.cmd install
npm.cmd run desktop:dev
~~~

### Validate the desktop application

~~~powershell
npm.cmd run check
npm.cmd run build
cargo test --manifest-path src-tauri\Cargo.toml
~~~

### Build and validate the catalog

The review manifest is the ordered input for a reproducible data build. Release data is stored in artifacts/, never Vite's disposable dist/ directory.

~~~powershell
python ingestion\build_index.py --manifest data\review\manifest.json --output artifacts\lexicon-error-2026.08-reviewed.db
python ingestion\test_pipeline.py --database artifacts\lexicon-error-2026.08-reviewed.db
~~~

### Package native desktop artifacts

~~~powershell
npm.cmd run desktop:build
~~~

On Windows this creates NSIS and MSI bundles under src-tauri/target/release/bundle/. Build on macOS or Linux to create their native bundles; the codebase is cross-platform, but release artifacts must be built for each target.

## Local CLI

~~~powershell
.\lexerror.cmd --database artifacts\lexicon-error-2026.08-reviewed.db coverage
.\lexerror.cmd --database artifacts\lexicon-error-2026.08-reviewed.db detect "error[E0382]: borrow of moved value"
.\lexerror.cmd --database artifacts\lexicon-error-2026.08-reviewed.db release-manifest --output artifacts\dataset-manifest.json
.\lexerror.cmd --database artifacts\lexicon-error-2026.08-reviewed.db export --format jsonl --output artifacts\lexicon-error.jsonl
~~~

JSON, JSONL, and CSV exports retain stable IDs and normalized metadata. Paste detection is local-only and redacts secret-bearing lines and obvious local paths before matching.

## Ingestion and provenance

Adapters in [ingestion/sources](ingestion/sources) transform a saved upstream snapshot or installed-tool output into the standardized entry format. Parsers do not perform network calls during normalization. The source lock records upstream URL, reference, retrieval timestamp, size, and SHA-256 hash.

The source registry includes license and redistribution guidance. The public corpus exports derived metadata only; it deliberately excludes raw source snapshots and local contribution directories. MDN-derived data retains page metadata rather than documentation bodies.

The original user-supplied root JSON files, including GPU records, remain unchanged. The organizer creates an auditable report that identifies canonical candidates, existing-diagnostic collisions, and source-less staging. See [data/review/user-import-report.json](data/review/user-import-report.json).

## Contributing diagnostics

Contributions may be JSON, JSONL, or Markdown with YAML frontmatter. Each contribution needs a stable identifier, real trigger, correction, and source provenance where available. Do not create one record for every variable-specific variation of the same diagnostic pattern.

~~~powershell
python ingestion\validate_entries.py path\to\entry.json
python ingestion\organize_user_records.py
~~~

See [CONTRIBUTING.md](CONTRIBUTING.md), [contributions/example.md](contributions/example.md), and [data/error-entry.schema.json](data/error-entry.schema.json). Local contributions remain local until an editor intentionally promotes them into a reviewed release.

## Hugging Face Dataset and Space

The repository contains two independently publishable Hub packages:

- [Dataset package](hf/lexiconerror-diagnostics/): 16,474 JSONL records, Dataset Card, source notices, schema, source lock, and SHA-256 release manifest.
- [Static Space](hf/lexiconerror-space/): a compute-free browser preview with an 80-record sample. It loads the full published corpus when its non-secret DATASET_URL variable is set.

Regenerate and validate both packages:

~~~powershell
python ingestion\package_hf_dataset.py
python ingestion\test_hf_package.py --package hf\lexiconerror-diagnostics --space hf\lexiconerror-space
~~~

The dataset intentionally declares license: other because it has composite source terms. Review [hf/lexiconerror-diagnostics/NOTICE.md](hf/lexiconerror-diagnostics/NOTICE.md) and [hf/PUBLISHING.md](hf/PUBLISHING.md) before public release.

## Privacy and security

- No analytics, account requirement, background network request, or hosted database is required for desktop use.
- Pasted diagnostics are analyzed locally; secret-like lines and obvious local paths are redacted before matching.
- Code examples are displayed, never executed.
- Exported databases may include user contributions and should be stored accordingly.
- External documentation links are user initiated.

Read [SECURITY.md](SECURITY.md) before reporting an issue that may involve sensitive data.

## GitHub readiness

The project includes:

- [Funding configuration](.github/FUNDING.yml) for [@theworker02](https://github.com/theworker02). The Sponsor button becomes actionable after the account activates GitHub Sponsors.
- Issue forms for catalog/application bugs and focused coverage or product requests.
- [Code of Conduct](.github/CODE_OF_CONDUCT.md), [support guidance](.github/SUPPORT.md), and a pull request template.
- A Windows pull-request validation workflow that checks TypeScript, Rust, the catalog build, and the Hugging Face packages without publishing anything.

The canonical repository is [theworker02/lexicon-error](https://github.com/theworker02/lexicon-error). Publishing remains an explicit maintainer action; the included workflows validate changes and deploy the static Pages site without requiring application secrets.

## Documentation

- [Architecture](ARCHITECTURE.md)
- [Contribution workflow](CONTRIBUTING.md)
- [Security and privacy](SECURITY.md)
- [Changelog](CHANGELOG.md)
- [Hugging Face publishing](hf/PUBLISHING.md)

## Roadmap

1. Curate more generated registry entries into fully verified records.
2. Expand state snapshots and cross-language conceptual mappings.
3. Publish the provenance-noticed Hugging Face Dataset and attach the static Space.
4. Add signed native release artifacts for supported desktop targets.
5. Add release automation after the GitHub repository and maintainer policy are confirmed.

## Support and funding

If LexiconError is useful, use the repository Sponsor button once the Magnexis GitHub Sponsors profile is active. The issue forms are intentionally structured so catalog corrections include enough source and reproduction detail to be actionable.
