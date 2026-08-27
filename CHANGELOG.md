# Changelog

## 1.0.0 - 2026-08-27

- Promoted LexiconError to its first stable semantic-versioned desktop release.
- Expanded the diagnostic inspector into four interactive workspaces: overview analytics, trigger-versus-fix, situational context and relationships, and failure-state provenance.
- Added catalog-derived frequency and failure-domain graphs with ecosystem-scoped interactive filters and explicit separation between curated likelihood and measured telemetry.
- Added resolvable cross-language diagnostic navigation, verification status, toolchain identity, version metadata, catalog cohort counts, and coverage quality.
- Refined the three-pane desktop interface with denser search results, clearer navigation hierarchy, accessible focus states, and reduced-motion behavior.
- Added a tested SQLite insights command and refreshed every README screenshot, GIF, and video from the compiled v1.0.0 desktop build.

## 2026.08

- Moved reproducible database outputs from the frontend's disposable `dist/` directory to `artifacts/`, preventing Vite builds from deleting release data before packaging or publication.
- Reworked the catalog surface into a dark command-first three-pane interface with hierarchical ecosystem filters, severity tones, root-cause/diff/context tabs, syntax-aware code comparisons, and a real Ctrl+K/Cmd+K global palette.
- Made `source_reference` a supported ingestion and contribution alias for canonical `source_url` provenance.
- Added normalized language, tool, concept, root-cause, provenance, relationship, fingerprint, and coverage metadata.
- Added source adapters for Roslyn, rustc, Clippy, CPython, V8, SpiderMonkey, Kotlin, SQLite, R, CUDA, HIP, OpenCL, Vulkan, and MDN with source manifest and hash locks.
- Expanded the manifest-built catalog to 16,474 records with conservative review status and quality accounting.
- Added Coverage Dashboard, paste-aware local detection, release manifests, machine-readable exports, and the `lexerror` maintenance CLI.
- Organized 1,207 supplied user records, including the NVIDIA/AMD GPU batch, into auditable canonical candidates, existing-diagnostic collisions, and source-less staging.
