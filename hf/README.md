# LexiconError on Hugging Face

![LexiconError logo](../assets/branding/lexiconerror-mark.svg)

This directory contains two independently publishable Hub repositories. The trained model package
is reproducibly generated under `artifacts/model/lexiconerror-router` by the versioned scripts in
`modeling/` and is published at
[`Magnexis/lexiconerror-router`](https://huggingface.co/Magnexis/lexiconerror-router).

- `lexiconerror-diagnostics/` is the provenance-preserving Dataset package. Its generated JSONL corpus, source notices, and release manifest are safe to upload together.
- `lexiconerror-space/` is a static HTML Space preview. It runs without compute and loads its bundled review sample by default. Set the non-secret Space variable `DATASET_URL` to the final dataset's `data/diagnostics.jsonl` URL to browse the full published corpus.

Generate or refresh both artifacts:

```powershell
python ingestion\package_hf_dataset.py
python ingestion\test_hf_package.py --package hf\lexiconerror-diagnostics --space hf\lexiconerror-space
```

Model training and validation:

```powershell
python modeling\train_router.py
python modeling\test_router.py
python -B modeling\test_model_package.py --package artifacts\model\lexiconerror-router
```

Publication remains an explicit maintainer action. The dataset and trained model use `license:
other` because source terms vary.
