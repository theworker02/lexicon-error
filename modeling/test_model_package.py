#!/usr/bin/env python3
"""Validate a generated LexiconError Router package before publication."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ModelPackageTests(unittest.TestCase):
    package = Path("artifacts/model/lexiconerror-router-medium")

    def test_required_release_files_exist(self) -> None:
        required = {
            "README.md",
            "config.json",
            "metrics.json",
            "requirements.txt",
            "SHA256SUMS.txt",
            "lexiconerror-router.joblib",
            "inference.py",
            "NOTICE.md",
            "assets/lexiconerror-mark.svg",
        }
        self.assertEqual([], sorted(str(path) for path in required if not (self.package / path).is_file()))

    def test_hash_and_dataset_identity_are_exact(self) -> None:
        config = json.loads((self.package / "config.json").read_text(encoding="utf-8"))
        model = self.package / "lexiconerror-router.joblib"
        self.assertEqual(config["model_sha256"], sha256_file(model))
        self.assertEqual(config["dataset_id"], "Magnexis/lexiconerror-diagnostics")
        self.assertEqual(config["total_records"], 16_474)
        self.assertEqual(config["targets"], ["language", "category", "severity"])
        self.assertIn(config["model_size"], {"small", "medium", "large"})
        self.assertEqual(config["hf_repo_id"], f"Magnexis/lexiconerror-router-{config['model_size']}")
        self.assertGreater(config["parameter_count"], 0)
        self.assertGreater(config["feature_count"], 0)

    def test_metrics_are_real_and_bounded(self) -> None:
        metrics = json.loads((self.package / "metrics.json").read_text(encoding="utf-8"))
        self.assertEqual(set(metrics), {"language", "category", "severity"})
        for values in metrics.values():
            self.assertGreater(values["evaluation_support"], 3_000)
            for key in ("accuracy", "balanced_accuracy", "macro_f1", "weighted_f1", "top_3_accuracy"):
                self.assertGreaterEqual(values[key], 0.0)
                self.assertLessEqual(values[key], 1.0)

    def test_packaged_inference_routes_known_diagnostics(self) -> None:
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location("lexiconerror_inference", self.package / "inference.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        model = module.load_model(self.package / "lexiconerror-router.joblib")
        cases = (
            ("error[E0382]: borrow of moved value", "Rust"),
            ("Traceback: KeyError: missing_key", "Python"),
            ("TS2322: Type string is not assignable to type number", "TypeScript"),
            ("CUDA error: an illegal memory access was encountered", "CUDA"),
        )
        for text, expected_language in cases:
            with self.subTest(text=text):
                result = module.predict(text, model, top_k=3)
                self.assertEqual(result["language"][0]["label"], expected_language)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=ModelPackageTests.package)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    ModelPackageTests.package = arguments.package
    unittest.main(argv=[__file__], verbosity=2)
