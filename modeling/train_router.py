#!/usr/bin/env python3
"""Train the LexiconError diagnostic router from the published JSONL corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
from sklearn.pipeline import FeatureUnion
from sklearn.linear_model import SGDClassifier


TARGETS = ("language", "category", "severity")
MODEL_NAME = "LexiconError Router"
MODEL_VERSION = "1.0.0"
DATASET_ID = "Magnexis/lexiconerror-diagnostics"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            missing = [field for field in ("id", *TARGETS) if not record.get(field)]
            if missing:
                raise ValueError(f"line {line_number} is missing required fields: {missing}")
            records.append(record)
    if not records:
        raise ValueError("training dataset is empty")
    return records


def render_input(record: dict[str, Any]) -> str:
    """Create the user-visible diagnostic text used for both training and inference."""
    fields = (
        ("code", record.get("code")),
        ("title", record.get("title")),
        ("message", record.get("description")),
        ("context", record.get("situational_context")),
        ("trigger", record.get("bad_example")),
    )
    return "\n".join(f"{label}: {str(value).strip()}" for label, value in fields if value).strip()


def deterministic_split(
    records: list[dict[str, Any]], test_ratio: float = 0.2
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build a stable split while keeping singleton labels in the training set."""
    language_groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        language_groups.setdefault(str(record["language"]), []).append(record)

    train: list[dict[str, Any]] = []
    test: list[dict[str, Any]] = []
    for group in language_groups.values():
        ordered = sorted(
            group,
            key=lambda item: hashlib.sha256(str(item["id"]).encode("utf-8")).hexdigest(),
        )
        if len(ordered) < 5:
            train.extend(ordered)
            continue
        test_count = max(1, min(len(ordered) - 1, round(len(ordered) * test_ratio)))
        test.extend(ordered[:test_count])
        train.extend(ordered[test_count:])

    # Evaluation must not contain a label the fitted heads have never seen.
    changed = True
    while changed:
        changed = False
        train_labels = {target: {str(row[target]) for row in train} for target in TARGETS}
        retained: list[dict[str, Any]] = []
        for record in test:
            if any(str(record[target]) not in train_labels[target] for target in TARGETS):
                train.append(record)
                changed = True
            else:
                retained.append(record)
        test = retained

    if not train or not test:
        raise ValueError("unable to create non-empty train and evaluation splits")
    return train, test


def make_vectorizer(max_features: int = 100_000) -> FeatureUnion:
    word_features = max(2_000, max_features // 2)
    char_features = max(2_000, max_features - word_features)
    return FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    analyzer="word",
                    ngram_range=(1, 2),
                    # Official diagnostic codes are often unique and are high-value routing signals.
                    min_df=1,
                    max_df=0.995,
                    max_features=word_features,
                    strip_accents="unicode",
                    sublinear_tf=True,
                    dtype=np.float32,
                ),
            ),
            (
                "character",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    min_df=1,
                    max_features=char_features,
                    sublinear_tf=True,
                    dtype=np.float32,
                ),
            ),
        ]
    )


def fit_router(
    train_records: list[dict[str, Any]], max_features: int = 100_000
) -> tuple[FeatureUnion, dict[str, SGDClassifier]]:
    texts = [render_input(record) for record in train_records]
    vectorizer = make_vectorizer(max_features=max_features)
    matrix = vectorizer.fit_transform(texts)
    verification_weight = np.asarray(
        [1.5 if record.get("verification_status") == "Verified" else 1.0 for record in train_records],
        dtype=np.float32,
    )
    classifiers: dict[str, SGDClassifier] = {}
    for index, target in enumerate(TARGETS):
        labels = [str(record[target]) for record in train_records]
        counts = Counter(labels)
        class_count = len(counts)
        # Full inverse-frequency balancing makes singleton diagnostics dominate ordinary queries.
        # Square-root balancing retains rare-label influence while the clip bounds probabilities.
        class_weights = {
            label: float(np.clip(np.sqrt(len(labels) / (class_count * count)), 0.5, 4.0))
            for label, count in counts.items()
        }
        sample_weight = verification_weight * np.asarray(
            [class_weights[label] for label in labels], dtype=np.float32
        )
        classifier = SGDClassifier(
            loss="log_loss",
            penalty="l2",
            alpha=1e-5,
            max_iter=2_000,
            tol=1e-4,
            class_weight=None,
            random_state=42 + index,
            n_jobs=-1,
        )
        classifier.fit(matrix, labels, sample_weight=sample_weight)
        classifiers[target] = classifier
    return vectorizer, classifiers


def evaluate_router(
    vectorizer: FeatureUnion,
    classifiers: dict[str, SGDClassifier],
    test_records: list[dict[str, Any]],
) -> dict[str, Any]:
    matrix = vectorizer.transform([render_input(record) for record in test_records])
    metrics: dict[str, Any] = {}
    for target, classifier in classifiers.items():
        expected = np.asarray([str(record[target]) for record in test_records])
        predicted = classifier.predict(matrix)
        probabilities = classifier.predict_proba(matrix)
        top_k = min(3, len(classifier.classes_))
        class_positions = {label: index for index, label in enumerate(classifier.classes_)}
        top_indices = np.argpartition(probabilities, -top_k, axis=1)[:, -top_k:]
        top_hits = [class_positions[label] in indices for label, indices in zip(expected, top_indices)]
        support = Counter(expected.tolist())
        metrics[target] = {
            "accuracy": round(float(accuracy_score(expected, predicted)), 6),
            "balanced_accuracy": round(float(balanced_accuracy_score(expected, predicted)), 6),
            "macro_f1": round(float(f1_score(expected, predicted, average="macro", zero_division=0)), 6),
            "weighted_f1": round(float(f1_score(expected, predicted, average="weighted", zero_division=0)), 6),
            "top_3_accuracy": round(float(np.mean(top_hits)), 6),
            "classes_trained": int(len(classifier.classes_)),
            "classes_evaluated": int(len(support)),
            "evaluation_support": int(len(expected)),
        }
    return metrics


def predict_text(
    bundle: dict[str, Any], text: str, top_k: int = 3
) -> dict[str, list[dict[str, Any]]]:
    matrix = bundle["vectorizer"].transform([text])
    output: dict[str, list[dict[str, Any]]] = {}
    for target, classifier in bundle["classifiers"].items():
        probabilities = classifier.predict_proba(matrix)[0]
        indices = np.argsort(probabilities)[::-1][: max(1, min(top_k, len(probabilities)))]
        output[target] = [
            {"label": str(classifier.classes_[index]), "confidence": round(float(probabilities[index]), 6)}
            for index in indices
        ]
    return output


def model_card(metadata: dict[str, Any], metrics: dict[str, Any]) -> str:
    metric_rows = "\n".join(
        f"| {target.title()} | {values['accuracy']:.3f} | {values['macro_f1']:.3f} | "
        f"{values['weighted_f1']:.3f} | {values['top_3_accuracy']:.3f} |"
        for target, values in metrics.items()
    )
    return f"""---
library_name: scikit-learn
pipeline_tag: text-classification
inference: false
license: other
datasets:
- {DATASET_ID}
tags:
- developer-tools
- compiler-diagnostics
- runtime-exceptions
- error-classification
- tfidf
widget:
- text: "error[E0382]: borrow of moved value: value"
  example_title: Rust ownership diagnostic
- text: "Traceback: KeyError: missing_key"
  example_title: Python runtime exception
- text: "CUDA error: an illegal memory access was encountered"
  example_title: CUDA memory fault
---

# {MODEL_NAME}

![LexiconError logo](assets/lexiconerror-mark.svg)

{MODEL_NAME} is a compact, CPU-friendly diagnostic-routing model trained on
[{DATASET_ID}](https://huggingface.co/datasets/{DATASET_ID}). Given an error message, stack trace,
compiler diagnostic, or nearby trigger snippet, it predicts the likely programming language,
diagnostic category, and severity. It does not generate fixes or execute supplied code.

## Evaluation

The model uses a deterministic 80/20 split grouped within each language. Singleton and otherwise
unseen labels stay in the training split. Inputs exclude explicit language, category, severity,
tool, and source fields to avoid direct metadata leakage.

| Head | Accuracy | Macro F1 | Weighted F1 | Top-3 accuracy |
| --- | ---: | ---: | ---: | ---: |
{metric_rows}

- Training records: {metadata['train_records']:,}
- Evaluation records: {metadata['evaluation_records']:,}
- Dataset SHA-256: `{metadata['dataset_sha256']}`
- Random seed: 42
- Runtime: scikit-learn {metadata['sklearn_version']}, Python {metadata['python_version']}

Full machine-readable results are in `metrics.json`.

## Usage

~~~python
import joblib

bundle = joblib.load("lexiconerror-router.joblib")
text = "error[E0382]: borrow of moved value: `value`"
matrix = bundle["vectorizer"].transform([text])
for head, classifier in bundle["classifiers"].items():
    print(head, classifier.predict(matrix)[0])
~~~

Loading a joblib/pickle artifact can execute code. Only load this file from the official Magnexis
repository or after verifying `SHA256SUMS.txt`.

## Training data and approval status

All {metadata['total_records']:,} structured records were eligible for training. `Verified` records
receive a modest 1.5x sample weight; `Needs Review` records remain explicitly unapproved and are not
misrepresented as editorially verified. The target labels are catalog-routing metadata, not proof
that every explanation or remediation is correct.

## Limitations

- Registry-derived templates and repeated diagnostic families can make held-out scores optimistic.
- Rare labels may have too little evaluation support for reliable per-class conclusions.
- Confidence values are classifier probabilities, not guarantees of diagnostic correctness.
- The model should route a query into LexiconError; it should not replace official compiler or
  runtime documentation, security review, or human debugging.
- Upstream data terms vary, so the model uses `license: other`; review the dataset NOTICE before
  redistribution.

## Reproduction

~~~powershell
python modeling\\train_router.py --dataset hf\\lexiconerror-diagnostics\\data\\diagnostics.jsonl --output artifacts\\model\\lexiconerror-router
python modeling\\test_router.py
~~~
"""


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def train(dataset: Path, output: Path, max_features: int = 100_000) -> dict[str, Any]:
    records = load_records(dataset)
    train_records, test_records = deterministic_split(records)
    vectorizer, classifiers = fit_router(train_records, max_features=max_features)
    metrics = evaluate_router(vectorizer, classifiers, test_records)
    metadata = {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "dataset_id": DATASET_ID,
        "dataset_sha256": sha256_file(dataset),
        "total_records": len(records),
        "train_records": len(train_records),
        "evaluation_records": len(test_records),
        "targets": list(TARGETS),
        "max_features": max_features,
        "random_seed": 42,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python_version": platform.python_version(),
        "sklearn_version": sklearn.__version__,
        "label_counts": {
            target: dict(sorted(Counter(str(row[target]) for row in records).items()))
            for target in TARGETS
        },
    }
    bundle = {"vectorizer": vectorizer, "classifiers": classifiers, "metadata": metadata}

    output.mkdir(parents=True, exist_ok=True)
    model_path = output / "lexiconerror-router.joblib"
    joblib.dump(bundle, model_path, compress=3)
    metadata["model_sha256"] = sha256_file(model_path)
    metadata["model_bytes"] = model_path.stat().st_size
    write_json(output / "config.json", metadata)
    write_json(output / "metrics.json", metrics)
    (output / "requirements.txt").write_text(
        f"scikit-learn=={sklearn.__version__}\njoblib>=1.4,<2\n", encoding="utf-8"
    )
    (output / "README.md").write_text(model_card(metadata, metrics), encoding="utf-8")
    (output / "SHA256SUMS.txt").write_text(
        f"{metadata['model_sha256']}  {model_path.name}\n", encoding="utf-8"
    )
    source_dir = Path(__file__).resolve().parent
    (output / "inference.py").write_bytes((source_dir / "inference.py").read_bytes())
    (output / "NOTICE.md").write_text(
        """# Model notice

LexiconError Router was trained from `Magnexis/lexiconerror-diagnostics` release 2026.08.
The corpus is composite derived metadata with source-specific upstream terms and is distributed as
`license: other`. This model does not supersede those terms. Review the dataset NOTICE and source
manifest before redistributing or using the model beyond diagnostic routing and research.

The model contains no executable code snippets from the dataset. Its joblib container uses Python
pickle semantics and must only be loaded from a trusted source after checksum verification.
""",
        encoding="utf-8",
    )
    assets = output / "assets"
    assets.mkdir(exist_ok=True)
    logo = Path(__file__).resolve().parents[1] / "assets" / "branding" / "lexiconerror-mark.svg"
    (assets / logo.name).write_bytes(logo.read_bytes())
    return {"metadata": metadata, "metrics": metrics, "output": str(output)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("hf/lexiconerror-diagnostics/data/diagnostics.jsonl"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/model/lexiconerror-router")
    )
    parser.add_argument("--max-features", type=int, default=100_000)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    result = train(arguments.dataset, arguments.output, arguments.max_features)
    print(json.dumps(result, indent=2))
