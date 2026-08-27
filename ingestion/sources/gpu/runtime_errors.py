#!/usr/bin/env python3
"""Extract CUDA and HIP runtime error enums from official vendor API references."""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

CUDA_URL = "https://docs.nvidia.com/cuda/cuda-runtime-api/group__CUDART__TYPES.html"
HIP_URL = "https://rocm.docs.amd.com/projects/HIP/en/latest/doxygen/html/hip__runtime__api_8h.html"
CUDA = re.compile(r"<dt><span class=\"enum-member-name-def\">(?P<code>cudaError[A-Za-z0-9_]+)\s*=.*?</span></dt>\s*<dd>(?P<description>.*?)</dd>", re.DOTALL)
HIP = re.compile(r"<h2 class=\"memtitle\".*?</span>(?P<code>hipError[A-Za-z0-9_]+)</h2>.*?<td class=\"memname\">.*?=\s*(?P<number>[^<]+)</td>.*?<div class=\"memdoc\">(?P<description>.*?)</div>", re.DOTALL)


def plain(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def category(code: str) -> str:
    value = code.lower()
    if any(token in value for token in ("memory", "address", "pointer", "managed")):
        return "Memory"
    if any(token in value for token in ("launch", "stream", "synchronize", "notready", "timeout")):
        return "Concurrency"
    if any(token in value for token in ("invalid", "configuration", "device", "context")):
        return "Runtime"
    return "Runtime"


def entry(*, language: str, prefix: str, code: str, description: str, source_url: str) -> dict[str, object]:
    return {
        "id": f"{prefix}_official_{code.lower()}",
        "language": language,
        "code": code,
        "category": category(code),
        "severity": "Runtime Exception",
        "title": code,
        "description": f"{description} This is the vendor-defined runtime error value; a minimal trigger and hardened repair are pending editorial review.",
        "bad_example": "// Registry-only record; a minimal reproduction is pending editorial review.",
        "good_example": "// Registry-only record; a source-backed repair is pending editorial review.",
        "version_introduced": None,
        "version_deprecated": None,
        "source_url": source_url,
        "tier": 3,
        "frequency": "Uncommon",
        "situational_context": [f"{language} runtime API", "GPU device execution"],
        "interaction_types": ["runtime"],
        "related_errors": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cuda", type=Path, required=True)
    parser.add_argument("--hip", type=Path, required=True)
    parser.add_argument("--cuda-output", type=Path, required=True)
    parser.add_argument("--hip-output", type=Path, required=True)
    args = parser.parse_args()
    cuda_entries = [entry(language="CUDA", prefix="cuda", code=match.group("code"), description=plain(match.group("description")), source_url=CUDA_URL) for match in CUDA.finditer(args.cuda.read_text(encoding="utf-8"))]
    hip_entries = [entry(language="ROCm / HIP", prefix="hip", code=match.group("code"), description=plain(match.group("description")) or f"HIP runtime error value {match.group('number').strip()}.", source_url=HIP_URL) for match in HIP.finditer(args.hip.read_text(encoding="utf-8"))]
    for output, entries in ((args.cuda_output, cuda_entries), (args.hip_output, hip_entries)):
        unique = {str(item["code"]): item for item in entries}
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(sorted(unique.values(), key=lambda item: str(item["code"])), indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len({item['code'] for item in cuda_entries})} CUDA and {len({item['code'] for item in hip_entries})} HIP runtime error values.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
