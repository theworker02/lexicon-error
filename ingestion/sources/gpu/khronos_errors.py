#!/usr/bin/env python3
"""Extract standard Vulkan and OpenCL failure result codes from Khronos headers."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

VULKAN_URL = "https://github.com/KhronosGroup/Vulkan-Headers/blob/main/include/vulkan/vulkan_core.h"
OPENCL_URL = "https://github.com/KhronosGroup/OpenCL-Headers/blob/main/CL/cl.h"
VULKAN_RESULT = re.compile(r"typedef enum VkResult \{(?P<body>.*?)\} VkResult;", re.DOTALL)
VULKAN_CODE = re.compile(r"\b(VK_(?:ERROR|INCOMPLETE|NOT_READY|TIMEOUT)_[A-Z0-9_]+|VK_(?:NOT_READY|TIMEOUT|INCOMPLETE))\s*=\s*(-?\d+)")
OPENCL_CODE = re.compile(r"^#define\s+(CL_(?:DEVICE_NOT_FOUND|DEVICE_NOT_AVAILABLE|COMPILER_NOT_AVAILABLE|MEM_OBJECT_ALLOCATION_FAILURE|OUT_OF_RESOURCES|OUT_OF_HOST_MEMORY|PROFILING_INFO_NOT_AVAILABLE|MEM_COPY_OVERLAP|IMAGE_FORMAT_MISMATCH|IMAGE_FORMAT_NOT_SUPPORTED|BUILD_PROGRAM_FAILURE|MAP_FAILURE|MISALIGNED_SUB_BUFFER_OFFSET|EXEC_STATUS_ERROR_FOR_EVENTS_IN_WAIT_LIST|COMPILE_PROGRAM_FAILURE|LINKER_NOT_AVAILABLE|LINK_PROGRAM_FAILURE|DEVICE_PARTITION_FAILED|KERNEL_ARG_INFO_NOT_AVAILABLE|INVALID_[A-Z0-9_]+))\s+(-\d+)", re.MULTILINE)


def category(code: str) -> str:
    value = code.lower()
    if any(token in value for token in ("memory", "out_of_host", "out_of_device", "allocation", "map_failure")):
        return "Memory"
    if any(token in value for token in ("timeout", "not_ready", "event", "synchronization")):
        return "Concurrency"
    if any(token in value for token in ("device_lost", "device_not", "driver")):
        return "Runtime"
    if any(token in value for token in ("invalid", "format", "argument", "parameter")):
        return "Type System"
    return "Runtime"


def build_entry(language: str, prefix: str, code: str, number: str, source_url: str) -> dict[str, object]:
    return {
        "id": f"{prefix}_{code.lower()}",
        "language": language,
        "code": code,
        "category": category(code),
        "severity": "Runtime Exception",
        "title": code.replace("_", " ").title(),
        "description": f"{language} standardized result code {code} ({number}) declared in the Khronos API header. The precise call pattern and hardened recovery guidance are pending editorial review.",
        "bad_example": "// Registry-only record; a minimal reproduction is pending editorial review.",
        "good_example": "// Registry-only record; a source-backed repair is pending editorial review.",
        "version_introduced": None,
        "version_deprecated": None,
        "source_url": source_url,
        "tier": 3,
        "frequency": "Uncommon",
        "situational_context": [f"{language} API", "GPU device execution"],
        "interaction_types": ["runtime"],
        "related_errors": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vulkan", type=Path, required=True)
    parser.add_argument("--opencl", type=Path, required=True)
    parser.add_argument("--vulkan-output", type=Path, required=True)
    parser.add_argument("--opencl-output", type=Path, required=True)
    args = parser.parse_args()
    result = VULKAN_RESULT.search(args.vulkan.read_text(encoding="utf-8"))
    if not result:
        raise ValueError("Could not locate VkResult in the Vulkan header")
    vulkan = [build_entry("Vulkan", "vk", code, number, VULKAN_URL) for code, number in VULKAN_CODE.findall(result.group("body"))]
    opencl = [build_entry("OpenCL", "cl", code, number, OPENCL_URL) for code, number in OPENCL_CODE.findall(args.opencl.read_text(encoding="utf-8"))]
    for output, entries in ((args.vulkan_output, vulkan), (args.opencl_output, opencl)):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(vulkan)} Vulkan and {len(opencl)} OpenCL error result codes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
