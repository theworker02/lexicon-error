---
title: LexiconError Demo
emoji: "⚠️"
colorFrom: slate
colorTo: blue
sdk: static
app_file: index.html
pinned: false
license: other
---

# LexiconError Demo

![LexiconError logo](assets/lexiconerror-mark.svg)

A static, compute-free preview of the LexiconError diagnostics corpus.

## What the Space demonstrates

- Client-side search across diagnostic code, title, explanation, language, and category.
- Language and severity filters with a master-detail inspector.
- Trigger and hardened-fix code panes without executing supplied snippets.
- Source links and verification status shown as reference metadata.

The complete Tauri desktop application remains the offline-first product. This Space is intentionally a public discovery and reference surface, not a remote execution or paste-upload service.

By default this Space loads the bundled 80-record sample. To browse a published catalog, define the **public, non-secret** Space variable `DATASET_URL` with the fully resolved URL to the dataset's `data/diagnostics.jsonl` file, for example:

```text
https://huggingface.co/datasets/Magnexis/lexiconerror-diagnostics/resolve/main/data/diagnostics.jsonl
```

The browser fetches and searches the JSONL directly. It does not execute examples, collect telemetry, or upload pasted diagnostics. The native Tauri application remains the complete offline product; this Space is a discovery and reference surface.

## Local preview

Serve this directory with any static file server after generating the sample:

```powershell
python ingestion\package_hf_dataset.py
python -m http.server 8080 --directory hf\lexiconerror-space
```

Open `http://localhost:8080`. Press `/` to focus search. The static Space needs no secret, GPU, persistent storage, or backend process.
