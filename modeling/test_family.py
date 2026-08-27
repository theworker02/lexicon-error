#!/usr/bin/env python3
"""Validate monotonic sizing and package identity for the router family."""

from __future__ import annotations

import argparse
import json
import unittest
from pathlib import Path

from train_router import SIZE_PROFILES


class RouterFamilyTests(unittest.TestCase):
    root = Path("artifacts/model")

    def configs(self) -> list[dict]:
        return [
            json.loads((self.root / f"lexiconerror-router-{size}" / "config.json").read_text(encoding="utf-8"))
            for size in SIZE_PROFILES
        ]

    def test_profiles_have_strictly_increasing_budgets(self) -> None:
        budgets = [int(profile["max_features"]) for profile in SIZE_PROFILES.values()]
        self.assertEqual(budgets, sorted(set(budgets)))

    def test_packages_have_strictly_increasing_parameters_and_bytes(self) -> None:
        configs = self.configs()
        self.assertEqual([config["model_size"] for config in configs], list(SIZE_PROFILES))
        for field in ("feature_count", "parameter_count", "model_bytes"):
            values = [int(config[field]) for config in configs]
            self.assertEqual(values, sorted(set(values)), f"{field} must increase: {values}")

    def test_repositories_and_checkpoints_are_distinct(self) -> None:
        configs = self.configs()
        self.assertEqual(len({config["hf_repo_id"] for config in configs}), 3)
        self.assertEqual(len({config["model_sha256"] for config in configs}), 3)
        for config in configs:
            self.assertEqual(config["dataset_sha256"], "5adb619e064b389f4e81adac9ce5ebb7156dfb63540ea9ae83d7d652c09fb897")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=RouterFamilyTests.root)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    RouterFamilyTests.root = arguments.root
    unittest.main(argv=[__file__], verbosity=2)
