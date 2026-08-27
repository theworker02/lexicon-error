# Security and privacy

LexiconError is offline-first. The desktop application does not enable telemetry, make background network calls, execute supplied snippets, or expose arbitrary shell access to the renderer.

Paste detection accepts at most 16 KiB, drops secret-bearing lines and obvious local paths before matching, and never uploads diagnostic text. Source downloads are explicit ingestion commands run by a developer; source snapshots are hash-locked for review. Imported contribution files are parsed as data and validated before SQLite insertion.

The current desktop build does not run an unauthenticated local HTTP API. Treat exported databases as potentially containing locally contributed diagnostic text and store them accordingly.
