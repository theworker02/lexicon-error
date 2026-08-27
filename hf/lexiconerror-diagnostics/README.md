---
language:
- en
pretty_name: LexiconError Diagnostics
license: other
size_categories:
- 10K<n<100K
tags:
- programming-languages
- compiler-diagnostics
- runtime-exceptions
- developer-tools
- cuda
- rocm
configs:
- config_name: diagnostics
  data_files:
  - split: train
    path: data/diagnostics.jsonl
---

# LexiconError Diagnostics

![LexiconError logo](assets/lexiconerror-mark.svg)

LexiconError Diagnostics is a 16,474-record, provenance-preserving corpus of programming-language compiler diagnostics, linter rules, runtime exceptions, infrastructure failures, and accelerator-runtime faults. It is a reference dataset, not a claim of exhaustive or fully editorially verified coverage.

## Dataset details

- Release version: `2026.08`
- Records: 16,474 across 44 languages and 45 tools
- Records marked verified: 41; generated registry records remain `Needs Review`
- Format: UTF-8 JSON Lines, one diagnostic per row
- Split: `train` is a catalog split, **not** a machine-learning train/validation recommendation

## Fields

Each row has a stable `id`, language/tool identity, code, category, severity, title, explanation, broken and corrected snippets, optional version bounds, classification/frequency/context fields, source URLs, normalized provenance, and verification state. `source_reference` mirrors the canonical `source_url` for contribution-format compatibility.

## Intended uses

- Offline developer reference, search, diagnostics grouping, evaluation fixtures, and retrieval experiments.
- Building tools that link back to official documentation.

Do not treat a `Needs Review` entry as verified remediation guidance, execute included snippets without isolation, or use this corpus as a replacement for current upstream compiler documentation.

## Provenance and licensing

This is a composite derived-metadata dataset. It deliberately excludes raw source snapshots and documentation bodies. Upstream terms vary by source; detailed license, attribution, source lock, and redistribution guidance are included in `metadata/`. The dataset is labelled `other` because no single blanket license can accurately supersede those upstream terms. See [NOTICE.md](NOTICE.md) and [LICENSE](LICENSE).

## Reproducibility

The dataset was generated from the SQLite release index with `ingestion/package_hf_dataset.py`. `metadata/release-manifest.json` records counts and SHA-256 hashes. The source snapshot lock is provided for auditability, but source snapshots themselves are intentionally omitted.
