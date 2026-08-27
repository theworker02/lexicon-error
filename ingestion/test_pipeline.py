#!/usr/bin/env python3
"""Regression checks for a built Lexicon Error database and Wave A source queues."""
from __future__ import annotations

import argparse
import json
import sqlite3
import unittest
from pathlib import Path

from coverage import coverage
from knowledge import detect, validate_knowledge

ROOT = Path(__file__).parents[1]
DATABASE: Path


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.connection = sqlite3.connect(DATABASE)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()

    def test_metadata_exists_for_every_entry(self) -> None:
        self.assertEqual(validate_knowledge(self.connection), [])

    def test_wave_a_coverage_is_real_database_output(self) -> None:
        by_language = {item["language"]: item for item in coverage(self.connection)}
        self.assertGreaterEqual(by_language["Rust"]["records"], 1_500)
        self.assertGreaterEqual(by_language["C#"]["records"], 2_000)
        self.assertGreaterEqual(by_language["Python"]["records"], 300)
        self.assertGreaterEqual(by_language["TypeScript"]["records"], 2_000)
        self.assertGreaterEqual(by_language["JavaScript"]["records"], 700)
        self.assertNotEqual(by_language["Rust"]["tier"], "Comprehensive")

    def test_expected_pastes_resolve_to_authoritative_identifiers(self) -> None:
        expected = {
            "error[E0382]: borrow of moved value": "E0382",
            "NameError: name 'foo' is not defined": "NameError",
            "TS2322: Type 'string' is not assignable to type 'number'.": "TS2322",
            "CS0246": "CS0246",
            "ERR_MODULE_NOT_FOUND": "ERR_MODULE_NOT_FOUND",
        }
        for pasted, code in expected.items():
            with self.subTest(code=code):
                matches = detect(self.connection, pasted)["matches"]
                self.assertTrue(matches, pasted)
                self.assertEqual(matches[0]["code"], code)

    def test_generated_adapter_queues_are_nontrivial_and_schema_shaped(self) -> None:
        minimums = {
            "csharp-roslyn-error-codes.json": 1_900,
            "rustc-lints.json": 200,
            "clippy-lints.json": 700,
            "python-stdlib-exceptions.json": 200,
            "python-stdlib-message-patterns.json": 1_800,
            "v8-message-templates.json": 300,
            "spidermonkey-message-definitions.json": 800,
            "mdn-javascript-errors.json": 120,
            "dotnet-runtime-exceptions.json": 170,
            "kotlin-compiler-diagnostics.json": 700,
            "sqlite-result-codes.json": 100,
            "r-runtime-messages.json": 20,
            "niche-language-examples.json": 25,
            "cuda-runtime-errors.json": 130,
            "hip-runtime-errors.json": 80,
            "vulkan-result-codes.json": 35,
            "opencl-error-codes.json": 60,
            "user-attributed-candidates.json": 40,
        }
        required = {"id", "language", "code", "category", "severity", "title", "description", "bad_example", "good_example", "source_url"}
        for name, minimum in minimums.items():
            with self.subTest(queue=name):
                entries = json.loads((ROOT / "data" / "review" / name).read_text(encoding="utf-8"))
                self.assertGreaterEqual(len(entries), minimum)
                self.assertTrue(all(required <= entry.keys() for entry in entries))

    def test_user_record_organization_preserves_auditable_dispositions(self) -> None:
        report = json.loads((ROOT / "data" / "review" / "user-import-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["received_records"], 1_207)
        self.assertEqual(report["unique_language_code_candidates"], 125)
        self.assertEqual(report["source_attributed_candidates"], 42)
        self.assertEqual(report["unattributed_staging_candidates"], 32)
        self.assertEqual(report["existing_canonical_collisions"], 51)
        self.assertTrue(all(item["disposition"] for item in report["records"]))


def main() -> int:
    global DATABASE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    DATABASE = args.database
    unittest.main(argv=["test_pipeline.py", *remaining], verbosity=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
