# Asset inventory â€” LexiconError

## Repository surfaces

| Asset | Location / notes |
|-------|------------------|
| Source tree | Repository root / language packages |
| Tests | `test/`, `tests/`, CI workflows if present |
| Docs | `README.md`, `docs/` |
| Diligence room | `docs/acquisition/` |
| License / notices | `LICENSE`, transition notices if present |
| Funding | `.github/FUNDING.yml` |
| CI | `.github/workflows/` if present |
| Branding | logos/assets folders if present |

## Capability highlights

- Official diagnostic identifiers are kept separate from human-readable titles.
- Severity, frequency, and taxonomy tier are independent fields rather than one vague priority score.
- Curated entries and generated registry imports expose different verification states.
- Source provenance remains attached to the diagnostic instead of being discarded during ingestion.
- Triggering code and hardened code are stored side by side.
- Related diagnostics can connect comparable concepts across languages without pretending their runtime semantics are identical.
- The desktop application, portable SQLite index, Hugging Face dataset, and routing models are separate outputs built from the same normalized knowledge layer.
- **Curated experience likelihood** is an ordinal classification: `Common`, `Uncommon`, `Rare`, or `Situational`.
- **Catalog distribution** is computed from the local SQLite database and shows how many indexed records in the selected ecosystem belong to each frequency or failure-domain bucket.
- Node.js 20 or newer
- Rust stable
- Python 3.11 or newer

## Usually excluded

Seller personal accounts, unrelated repos, and unreissued registry tokens â€” unless listed in the definitive agreement.

*Updated: 2026-09-22*
