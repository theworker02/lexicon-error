# Source ingestion and review queues

Collected and organized on 2026-08-27 for LexiconError's offline dataset. The exact release order is [manifest.json](manifest.json); source hash records are in [source-lock.json](source-lock.json).

| Source | Output | Records | Review status |
| --- | --- | ---: | --- |
| Rust compiler error index | `rust-error-stubs.json` | 518 | Official E-code identity; editorial examples pending. |
| rustc installed lint registry | `rustc-lints.json` | 241 | Tool-output registry; editorial examples pending. |
| Clippy installed lint registry | `clippy-lints.json` | 809 | Tool-output registry; editorial examples pending. |
| Roslyn ErrorCode enum | `csharp-roslyn-error-codes.json` | 1,999 | Official code identity; editorial explanations pending. |
| Microsoft C# preprocessor diagnostics | `csharp-preprocessor-stubs.json` | 35 | Official documentation subset; editorial examples pending. |
| CPython built-in exception inventory | `python-exception-stubs.json` | 70 | Runtime exception inventory; editorial review pending. |
| CPython standard library classes | `python-stdlib-exceptions.json` | 233 | Source-declared exception classes; editorial review pending. |
| CPython standard-library raise patterns | `python-stdlib-message-patterns.json` | 1,896 | Parameterized source signatures; editorial review pending. |
| TypeScript compiler package registry | `typescript-diagnostics.json` | 2,097 | Official compiler diagnostics; editorial review pending. |
| OpenJDK javac `compiler.properties` | `javac-diagnostics.json` | 687 | Official message templates; editorial review pending. |
| LLVM Clang semantic diagnostics | `clang-sema-diagnostics.json` | 4,641 | Official definitions; editorial review pending. |
| Node.js error-code documentation | `node-error-codes.json` | 423 | Official `ERR_*` registry; editorial review pending. |
| V8 message templates | `v8-message-templates.json` | 307 | Official runtime messages; editorial review pending. |
| SpiderMonkey message registry | `spidermonkey-message-definitions.json` | 806 | Mozilla runtime messages; editorial review pending. |
| MDN JavaScript error pages | `mdn-javascript-errors.json` | 131 | Page metadata only, separately attributed; editorial review pending. |
| Go type-checker registry | `go-type-errors.json` | 146 | Official stable codes. |
| Installed .NET exception inventory | `dotnet-runtime-exceptions.json` | 182 | Public runtime exception types; editorial review pending. |
| Kotlin K1 compiler registry | `kotlin-compiler-diagnostics.json` | 768 | JetBrains diagnostic identities; editorial review pending. |
| SQLite result codes | `sqlite-result-codes.json` | 103 | Public database-engine outcomes; editorial review pending. |
| R runtime messages | `r-runtime-messages.json` | 20 | Static R runtime signatures; editorial review pending. |
| Curated niche-language examples | `niche-language-examples.json` | 27 | Broken/fixed examples with per-entry source links. |
| NVIDIA CUDA runtime errors | `cuda-runtime-errors.json` | 136 | Official CUDA error values; editorial review pending. |
| AMD HIP runtime errors | `hip-runtime-errors.json` | 82 | Official ROCm/HIP error values; editorial review pending. |
| Khronos Vulkan result codes | `vulkan-result-codes.json` | 39 | Official Vulkan results; editorial review pending. |
| Khronos OpenCL error codes | `opencl-error-codes.json` | 61 | Official OpenCL errors; editorial review pending. |
| Source-attributed supplied records | `user-attributed-candidates.json` | 42 | Conservatively deduplicated user candidates; needs review. |

The manifest-built release contains 16,474 unique entries after stable-ID duplicate handling. Source-less supplied records remain in `user-unattributed-staging.json`; existing diagnostic collisions and every original supplied ID are documented in `user-import-report.json`.

Raw source snapshots are deliberately ignored by version control, but their source, retrieval date, byte count, and SHA-256 digest are committed in `source-lock.json`. The packaged application includes review queues but does not acquire or refresh sources on its own.
