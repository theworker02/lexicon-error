#!/usr/bin/env python3
"""Train all three separately sized LexiconError Router variants."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from train_router import SIZE_PROFILES, train, write_json


def train_family(dataset: Path, output_root: Path, sizes: list[str]) -> dict:
    variants = []
    for size in sizes:
        output = output_root / f"lexiconerror-router-{size}"
        result = train(dataset, output, size=size)
        metadata = result["metadata"]
        variants.append(
            {
                "size": size,
                "repo_id": metadata["hf_repo_id"],
                "feature_budget": metadata["max_features"],
                "feature_count": metadata["feature_count"],
                "parameter_count": metadata["parameter_count"],
                "model_bytes": metadata["model_bytes"],
                "model_sha256": metadata["model_sha256"],
                "metrics": result["metrics"],
                "output": result["output"],
            }
        )
    manifest = {
        "family": "LexiconError Router",
        "version": "1.0.0",
        "dataset": "Magnexis/lexiconerror-diagnostics",
        "variants": variants,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    write_json(output_root / "family-manifest.json", manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("hf/lexiconerror-diagnostics/data/diagnostics.jsonl"),
    )
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/model"))
    parser.add_argument("--sizes", nargs="+", choices=tuple(SIZE_PROFILES), default=list(SIZE_PROFILES))
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    print(json.dumps(train_family(arguments.dataset, arguments.output_root, arguments.sizes), indent=2))
