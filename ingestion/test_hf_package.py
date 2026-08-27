#!/usr/bin/env python3
"""Validate a local Hugging Face Dataset/Static Space release package."""
from __future__ import annotations

import argparse
import hashlib
import json
import unittest
from pathlib import Path

REQUIRED_RECORD_FIELDS = {
    "id", "canonical_id", "language", "tool_id", "code", "category", "severity", "title",
    "description", "bad_example", "good_example", "version_introduced", "version_deprecated",
    "source_url", "source_reference", "tier", "frequency", "situational_context",
    "interaction_types", "related_errors", "state_snapshot", "classifications",
    "normalized_severity", "fingerprint", "provenance", "verification_status",
}


class HuggingFacePackageTests(unittest.TestCase):
    package: Path
    space: Path

    def test_dataset_card_declares_supported_jsonl_config(self) -> None:
        card = (self.package / "README.md").read_text(encoding="utf-8")
        self.assertTrue(card.startswith("---\n"))
        self.assertIn("license: other", card)
        self.assertIn("config_name: diagnostics", card)
        self.assertIn("path: data/diagnostics.jsonl", card)
        self.assertIn("Needs Review", card)

    def test_records_are_valid_and_compatible_with_the_contribution_source_alias(self) -> None:
        records_path = self.package / "data" / "diagnostics.jsonl"
        records = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines() if line]
        self.assertGreaterEqual(len(records), 16_000)
        self.assertTrue(all(set(record) == REQUIRED_RECORD_FIELDS for record in records))
        self.assertTrue(all(record["source_reference"] == record["source_url"] for record in records))
        self.assertTrue(all(record["verification_status"] in {"Needs Review", "Verified"} for record in records))

    def test_manifest_hashes_and_notice_cover_the_release(self) -> None:
        manifest = json.loads((self.package / "metadata" / "release-manifest.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(manifest["records"], 16_000)
        self.assertIn("raw source snapshots", manifest["excludes"])
        for relative, detail in manifest["files"].items():
            path = self.package / relative
            self.assertTrue(path.is_file(), relative)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), detail["sha256"])
        notice = (self.package / "NOTICE.md").read_text(encoding="utf-8")
        self.assertIn("NVIDIA CUDA documentation", notice)
        self.assertIn("MDN contributors", notice)

    def test_static_space_is_configured_without_compute_or_secret_data(self) -> None:
        card = (self.space / "README.md").read_text(encoding="utf-8")
        script = (self.space / "app.js").read_text(encoding="utf-8")
        self.assertIn("sdk: static", card)
        self.assertIn("app_file: index.html", card)
        self.assertIn("DATASET_URL", card)
        self.assertIn("sample-data.json", script)
        self.assertNotIn("HF_TOKEN", script)
        sample = json.loads((self.space / "sample-data.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(sample), 40)
        self.assertTrue(all(REQUIRED_RECORD_FIELDS <= set(record) for record in sample))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--space", type=Path, required=True)
    args, remaining = parser.parse_known_args()
    HuggingFacePackageTests.package = args.package
    HuggingFacePackageTests.space = args.space
    unittest.main(argv=["test_hf_package.py", *remaining], verbosity=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
