# Lexicon Error architecture

```text
React / TypeScript UI
       | Tauri IPC
Rust commands and validation
       | SQLite + FTS5
Bundled review manifest / local contributions
       | Python source adapters and release tooling
```

`entries` is the backward-compatible renderer model. The normalized knowledge layer adds language, tool, concept, root-cause, metadata, and relationship tables without changing legacy IDs. Metadata carries source authority, review state, canonical identifier, fingerprint, and normalized severity.

## Desktop interaction model

The React shell is a persistent three-pane workspace: a domain-oriented sidebar writes the same validated facet filters used by search; the center pane is a compact FTS-ranked result grid; and the right inspector renders one selected record. The inspector tabs are presentation states over the same local record, keeping root cause, remediation diff, state snapshot, situational conditions, and provenance consistent. The Ctrl+K/Cmd+K palette calls the existing local search command and can also switch among catalog, matrix, and coverage views. No search request leaves the process.

Contribution parsers accept either `source_url` or `source_reference`; both normalize to the single persisted `entries.source_url` provenance column. This maintains a stable local database and backward compatibility while allowing generator-friendly source field naming.

The app runs no local HTTP listener. Native IPC exposes search, metadata, language/tool/concept profiles, coverage, detection, import, and backup operations. This avoids exposing an unauthenticated localhost API by default; a future API or MCP transport must use the same validated query layer.

The ingestion pipeline is staged: source snapshot, source adapter, schema validation, duplicate handling, knowledge enrichment, quality gates, then portable SQLite build. `data/review/manifest.json` defines the release input order.
