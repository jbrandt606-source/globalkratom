# OPMS full-text court PDF search — upload instructions

This package is designed for the existing GitHub Pages repository `jbrandt606-source/globalkratom`.

## Important: preserve the folder paths

**Upload the CONTENTS of this ZIP to the repository ROOT**, not into an extra folder called `opms_search_package`.

Files to add/replace:

- `opms/index.html` — main OPMS landing page (replaces the existing empty file)
- `opms/search.html` — PDF search interface (replaces the existing empty file)
- `opms/search.js` — browser search logic
- `scripts/build_opms_index.py` — PDF text and OCR indexing script
- `.github/workflows/opms-pdf-index.yml` — GitHub Actions workflow

Leave `opms/pdfs/` and all its existing PDFs unchanged.

## First run

1. Upload all five files to the paths above. Commit to `main`.
2. In GitHub, open **Actions** → **Index OPMS court PDFs** → **Run workflow** → **Run workflow**.
3. Wait for the workflow to finish successfully. The first run may take a long time because it OCRs image-only pages.
4. Confirm the repository now contains `opms/search-data/manifest.json` and multiple `chunk-XXXX.json` files.
5. Visit `https://globalkratom.org/opms/search.html` and search for a term known to be in one of your PDFs.

Subsequent changes to `opms/pdfs/` trigger a rebuild automatically. Unchanged PDFs reuse extracted text already committed in `opms/search-data/docs/`.

## Permissions

The workflow itself needs repository write permission to commit generated index data. GitHub repository **Settings → Actions → General → Workflow permissions → Read and write permissions** must allow this. If your organization blocks it, use the manual fallback below.

## Manual fallback

Run on a computer with Python 3.11+, PyMuPDF and Tesseract installed:

`python -m pip install pymupdf`

`python scripts/build_opms_index.py --root . --ocr auto`

Then upload the generated `opms/search-data/` folder to GitHub. This manual option does not require Actions write permissions.

## Important limitations

- The index searches actual extracted PDF page text, not merely filenames or descriptions. Filename/docket searches are not separately implemented; use the filing group selector for docket series.
- OCR is attempted on pages with fewer than 25 extracted characters. OCR quality varies and may miss handwriting, tiny print, or low-quality scans.
- Some pages are very long, and first-time loading all text shards may take time on mobile. This is a functional starter system, not yet a highly optimized production search service.
- The system indexes all PDFs in `opms/pdfs/`, including nested directories, but does not alter the original PDFs.
- The GitHub Actions workflow has a 350-minute timeout; very large scanned collections may need staged OCR or another build environment.
- Do not add sealed or private materials to a public repository. Review court documents for confidential personal information before publishing.
- The existing linked articles may refer to differently named PDFs in their old folders. Those older links are not automatically repaired by this package.
- The search uses simple substring matching for all/any words; this is not linguistic stemming or a legal-research query language.
