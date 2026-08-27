# Publishing LexiconError to Hugging Face

The generated directories are separate repositories:

- hf/lexiconerror-diagnostics: Dataset repository
- hf/lexiconerror-space: static HTML Space repository

## Preflight

```powershell
python ingestion\\build_index.py --manifest data\\review\\manifest.json --output artifacts\\lexicon-error-2026.08-reviewed.db
python ingestion\\package_hf_dataset.py
python ingestion\\test_hf_package.py --package hf\\lexiconerror-diagnostics --space hf\\lexiconerror-space
```

Review the Dataset NOTICE.md, LICENSE, and source manifest before choosing public visibility. The corpus uses license: other because upstream terms vary. Do not relabel it as a blanket open-data release without a source-by-source legal review.

## Dataset

Authenticate using `hf auth login` or an `HF_TOKEN` environment variable. The approved public dataset lives under the Magnexis organization:

```powershell
hf repos create Magnexis/lexiconerror-diagnostics --type dataset --public
hf upload Magnexis/lexiconerror-diagnostics hf\\lexiconerror-diagnostics --type dataset --commit-message "Release LexiconError Diagnostics 2026.08"
```

After upload, confirm that the Dataset Viewer recognizes the diagnostics configuration and train split. The Hub supports JSONL datasets and uses the YAML configs metadata in the dataset card to identify splits.

## Static Space

Create a static Space, then upload the Space directory:

```powershell
hf repos create Magnexis/lexiconerror-demo --type space --sdk static --public
hf upload Magnexis/lexiconerror-demo hf\\lexiconerror-space --type space --commit-message "Publish LexiconError static preview"
```

Set the public non-secret Space variable DATASET_URL to:

```text
https://huggingface.co/datasets/Magnexis/lexiconerror-diagnostics/resolve/main/data/diagnostics.jsonl
```

The Space has no model, no GPU requirement, no telemetry, and no secret-bearing runtime configuration. It falls back to its bundled 80-record preview until that variable is set.
