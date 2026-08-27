"""Minimal inference helper shipped with the LexiconError Router model."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np


def load_model(path: str | Path = "lexiconerror-router.joblib") -> dict[str, Any]:
    """Load a trusted LexiconError Router joblib bundle."""
    return joblib.load(path)


def predict(
    diagnostic: str, model: dict[str, Any], top_k: int = 3
) -> dict[str, list[dict[str, Any]]]:
    """Return ranked language, category, and severity predictions."""
    if not diagnostic.strip():
        raise ValueError("diagnostic text must not be empty")
    matrix = model["vectorizer"].transform([diagnostic])
    output: dict[str, list[dict[str, Any]]] = {}
    for target, classifier in model["classifiers"].items():
        probabilities = classifier.predict_proba(matrix)[0]
        indices = np.argsort(probabilities)[::-1][: max(1, min(top_k, len(probabilities)))]
        output[target] = [
            {"label": str(classifier.classes_[index]), "confidence": float(probabilities[index])}
            for index in indices
        ]
    return output
