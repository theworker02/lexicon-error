# LexiconError GitHub Pages site

![LexiconError logo](assets/lexiconerror-mark.svg)

This static site is the public discovery and download surface for people who use GitHub rather than Hugging Face. It does not replace the desktop application or send diagnostics to a server.

## What it contains

- Product overview and current catalog counts.
- Link to the latest GitHub Release for installers, MSI, portable database, checksums, and release notes.
- A local 80-record catalog preview with client-side search, trigger/fix views, and official source links.
- Data-provenance and privacy summary.

## Local preview

~~~powershell
python ingestion\package_hf_dataset.py
python -m http.server 8080 --directory site
~~~

Open http://localhost:8080. The browser preview uses only site/sample-data.json. It makes no telemetry, upload, or API request.

## Deployment

.github/workflows/pages.yml deploys the site from main using the GitHub Pages workflow. Before the first deploy, configure the repository Pages source as GitHub Actions. The page's release links target the repository's latest release endpoint.

