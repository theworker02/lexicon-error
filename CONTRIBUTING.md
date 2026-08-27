# Contributing diagnostics

Contributions are local JSON or Markdown records using [data/error-entry.schema.json](data/error-entry.schema.json). Use a stable, lowercase underscore-separated ID, cite an authoritative source whenever possible, and provide a real minimal trigger and correction. Use canonical `source_url` or the supported `source_reference` alias; both normalize to one stored provenance URL. Do not submit identifier-only variants; use a parameterized pattern or a materially distinct diagnostic instead.

```powershell
python ingestion/validate_entries.py path\to\entries.json
python ingestion/organize_user_records.py
python ingestion/build_index.py --manifest data/review/manifest.json --output artifacts\lexicon-error.db
python ingestion/test_pipeline.py --database artifacts\lexicon-error.db
```

Generated registry imports are `Needs Review`, not verified explanations. Promote an entry only after adding source-backed meaning, reproducible example, repair, and version information.
