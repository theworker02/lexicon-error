# Changelog

## 2026.08

- Moved reproducible database outputs from the frontend's disposable `dist/` directory to `artifacts/`, preventing Vite builds from deleting release data before packaging or publication.
- Reworked the catalog surface into a dark command-first three-pane interface with hierarchical ecosystem filters, severity tones, root-cause/diff/context tabs, syntax-aware code comparisons, and a real Ctrl+K/Cmd+K global palette.
- Made `source_reference` a supported ingestion and contribution alias for canonical `source_url` provenance.
- Added normalized language, tool, concept, root-cause, provenance, relationship, fingerprint, and coverage metadata.
- Added source adapters for Roslyn, rustc, Clippy, CPython, V8, SpiderMonkey, Kotlin, SQLite, R, CUDA, HIP, OpenCL, Vulkan, and MDN with source manifest and hash locks.
- Expanded the manifest-built catalog to 16,474 records with conservative review status and quality accounting.
- Added Coverage Dashboard, paste-aware local detection, release manifests, machine-readable exports, and the `lexerror` maintenance CLI.
- Organized 1,207 supplied user records, including the NVIDIA/AMD GPU batch, into auditable canonical candidates, existing-diagnostic collisions, and source-less staging.
