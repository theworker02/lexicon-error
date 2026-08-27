# Source adapters

Each adapter consumes a saved upstream snapshot and writes a JSON review queue. It does not contact the network while parsing, does not execute source material, and emits provenance suitable for the `data/knowledge/source-manifest.json` registry.

Snapshot acquisition is intentionally separate from parsing. `ingestion/fetch_official.py` stores an exact input file, and `ingestion/sources/snapshot_lock.py` records its URL, retrieval time, byte count, and SHA-256 digest. Review queues remain `Needs Review` until an editor adds a source-backed explanation, minimal reproduction, and correction.

The generated `code` is either an upstream code or a stable source-qualified diagnostic key. Source-qualified keys are not claimed to be persistent compiler error codes.
