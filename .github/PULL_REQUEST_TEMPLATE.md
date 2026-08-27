## Summary

Describe the change and the problem it solves.

## Catalog or ingestion impact

- [ ] No diagnostic data change
- [ ] Curated entry change
- [ ] Generated adapter or source-lock change
- [ ] Schema, migration, or normalization change
- [ ] Desktop UI or native command change
- [ ] Hugging Face package change

## Validation

List exact commands run and their results.

- [ ] npm.cmd run check
- [ ] npm.cmd run build
- [ ] cargo test --manifest-path src-tauri\Cargo.toml
- [ ] python ingestion\test_pipeline.py --database artifacts\lexicon-error-2026.08-reviewed.db
- [ ] python ingestion\test_hf_package.py --package hf\lexiconerror-diagnostics --space hf\lexiconerror-space

## Provenance and privacy

- [ ] I retained or added authoritative source attribution for diagnostic content.
- [ ] I did not add raw documentation bodies, credentials, private paths, or unreviewed sensitive data.
- [ ] I updated documentation where behavior or release process changed.

