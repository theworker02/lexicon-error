#!/usr/bin/env python3
"""Run local inference with the trained LexiconError router."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib

from train_router import predict_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", nargs="?", help="Diagnostic text; reads stdin when omitted")
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("artifacts/model/lexiconerror-router/lexiconerror-router.joblib"),
    )
    parser.add_argument("--top-k", type=int, default=3)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    diagnostic = arguments.text if arguments.text is not None else sys.stdin.read()
    if not diagnostic.strip():
        raise SystemExit("diagnostic text is required")
    model = joblib.load(arguments.model)
    print(json.dumps(predict_text(model, diagnostic, arguments.top_k), indent=2))
