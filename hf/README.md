# LexiconError on Hugging Face

This directory contains two independently publishable Hub repositories.

- `lexiconerror-diagnostics/` is the provenance-preserving Dataset package. Its generated JSONL corpus, source notices, and release manifest are safe to upload together.
- `lexiconerror-space/` is a static HTML Space preview. It runs without compute and loads its bundled review sample by default. Set the non-secret Space variable `DATASET_URL` to the final dataset's `data/diagnostics.jsonl` URL to browse the full published corpus.

Generate or refresh both artifacts:

```powershell
python ingestion\package_hf_dataset.py
python ingestion\test_hf_package.py --package hf\lexiconerror-diagnostics --space hf\lexiconerror-space
```

The publish commands are intentionally documented but not automated: creating a public repository and granting a release license are external publication decisions.

