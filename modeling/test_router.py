#!/usr/bin/env python3
"""Behavioral tests for the LexiconError router training and inference package."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from train_router import SIZE_PROFILES, deterministic_split, fit_router, predict_text, render_input


def fixture_record(index: int, language: str, category: str, severity: str, code: str) -> dict:
    return {
        "id": f"fixture_{index}",
        "language": language,
        "category": category,
        "severity": severity,
        "code": code,
        "title": f"{language} {category} diagnostic",
        "description": f"{language} compiler reports {code} during {category.lower()} analysis",
        "bad_example": f"trigger_{language}_{index}()",
        "verification_status": "Verified" if index % 2 else "Needs Review",
    }


class RouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = []
        for index in range(10):
            self.records.append(fixture_record(index, "Rust", "Memory", "Compiler Error", "E0382"))
        for index in range(10, 20):
            self.records.append(
                fixture_record(index, "Python", "Runtime", "Runtime Exception", "KeyError")
            )

    def test_render_input_excludes_target_metadata(self) -> None:
        rendered = render_input(self.records[0])
        self.assertIn("E0382", rendered)
        self.assertNotIn("severity:", rendered.lower())
        self.assertNotIn("language:", rendered.lower())

    def test_size_profiles_are_ordered_and_separate(self) -> None:
        budgets = [profile["max_features"] for profile in SIZE_PROFILES.values()]
        repositories = [profile["repo_id"] for profile in SIZE_PROFILES.values()]
        self.assertEqual(budgets, [25_000, 100_000, 250_000])
        self.assertEqual(len(set(repositories)), 3)

    def test_split_is_deterministic_and_preserves_labels(self) -> None:
        first = deterministic_split(self.records)
        second = deterministic_split(self.records)
        self.assertEqual([row["id"] for row in first[0]], [row["id"] for row in second[0]])
        self.assertEqual(len(first[0]), 16)
        self.assertEqual(len(first[1]), 4)
        self.assertEqual({row["language"] for row in first[1]}, {"Rust", "Python"})

    def test_training_produces_ranked_predictions(self) -> None:
        train, _ = deterministic_split(self.records)
        vectorizer, classifiers = fit_router(train, max_features=4_000)
        bundle = {"vectorizer": vectorizer, "classifiers": classifiers}
        result = predict_text(bundle, "error[E0382]: borrow of moved value", top_k=2)
        self.assertEqual(result["language"][0]["label"], "Rust")
        self.assertGreaterEqual(result["language"][0]["confidence"], 0.0)
        self.assertLessEqual(result["language"][0]["confidence"], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
