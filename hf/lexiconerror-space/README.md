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

A static, compute-free preview of the LexiconError diagnostics corpus.

By default this Space loads the bundled 80-record sample. To browse a published catalog, define the **public, non-secret** Space variable `DATASET_URL` with the fully resolved URL to the dataset's `data/diagnostics.jsonl` file, for example:

```text
https://huggingface.co/datasets/<namespace>/lexiconerror-diagnostics/resolve/main/data/diagnostics.jsonl
```

The browser fetches and searches the JSONL directly. It does not execute examples, collect telemetry, or upload pasted diagnostics. The native Tauri application remains the complete offline product; this Space is a discovery and reference surface.

