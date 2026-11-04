#!/usr/bin/env python3
"""Build Factor Eight's static PDF search index without changing any source file.

Install: python -m pip install 'PyMuPDF>=1.24,<2'
Run:     python scripts/build_factor8_index.py --root . --ocr off
Optional --ocr auto uses a locally installed Tesseract for scan-only pages.
The catalog is authoritative: deleted compilations and unlisted files are not indexed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import fitz
except ImportError:
    sys.exit("PyMuPDF is missing. Run: python -m pip install 'PyMuPDF>=1.24,<2'")

VERSION = 3
CHUNK_BYTES = 550_000

def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def useful_text(text: str) -> bool:
    """Do not mistake filing footers or a few diagram labels for page text."""
    cleaned = re.sub(r"Electronically Filed.{0,170}", " ", text, flags=re.I)
    cleaned = re.sub(r"Not an Official Court Document", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"(?:Author Manuscript\s*)+", " ", cleaned, flags=re.I)
    words = re.findall(r"[A-Za-z]{3,}", cleaned)
    return len(words) >= 18 and len(set(w.lower() for w in words)) >= 12

def ocr_page(page: fitz.Page, lang: str) -> str:
    with tempfile.TemporaryDirectory(prefix="factor8-ocr-") as td:
        image = Path(td) / "page.png"
        page.get_pixmap(matrix=fitz.Matrix(2, 2), colorspace=fitz.csGRAY, alpha=False).save(image)
        result = subprocess.run(
            ["tesseract", str(image), "stdout", "-l", lang],
            capture_output=True, text=True, timeout=100, check=False,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip()[:200])
        return compact(result.stdout)

def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root, not the factor8 folder")
    parser.add_argument("--ocr", choices=("off", "auto"), default="off")
    parser.add_argument("--lang", default="eng")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    site = root / "factor8"
    catalog_file = site / "catalog.json"
    if not catalog_file.is_file():
        sys.exit(f"Missing {catalog_file}. --root must point to the repository root.")
    catalog = json.loads(catalog_file.read_text(encoding="utf-8"))
    pdfs = [d for d in catalog if Path(d["path"]).suffix.lower() == ".pdf"]
    if not pdfs:
        sys.exit("No PDF entries in factor8/catalog.json; refusing to replace the index.")
    missing = [d["path"] for d in pdfs if not (site / d["path"]).is_file()]
    if missing:
        sys.exit("These catalog PDFs are missing. Match spelling and capitalization:\n" + "\n".join(missing))
    if args.ocr == "auto" and not shutil.which("tesseract"):
        sys.exit("--ocr auto requires Tesseract. Install it or run --ocr off.")
    out = site / "search-data"
    cache = out / "docs"
    cache.mkdir(parents=True, exist_ok=True)
    stats = dict(documents=0, pages=0, text_pages=0, native_pages=0, ocr_pages=0,
                 scan_only_pages=0, reviewed_excerpts=0, failed_documents=0)
    rows: list[dict] = []
    coverage: list[dict] = []
    issues: list[str] = []
    present_pages: set[tuple[str, int]] = set()
    active_cache: set[str] = set()
    for n, d in enumerate(pdfs, 1):
        source = site / d["path"]
        ident = d["id"]
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        dest = cache / f"{ident}.json"
        active_cache.add(dest.name)
        record = None
        if dest.exists():
            try:
                candidate = json.loads(dest.read_text(encoding="utf-8"))
                if (candidate.get("sha256") == digest and candidate.get("version") == VERSION
                    and (args.ocr == "off" or candidate.get("ocr_attempted"))):
                    record = candidate
            except (OSError, ValueError):
                pass
        if record is None:
            page_records, errors = [], []
            try:
                with fitz.open(source) as pdf:
                    for i, page in enumerate(pdf):
                        text = compact(page.get_text(sort=True))
                        mode = "text" if useful_text(text) else "empty"
                        if mode == "empty" and args.ocr == "auto":
                            try:
                                recognized = ocr_page(page, args.lang)
                                if useful_text(recognized):
                                    text, mode = recognized, "ocr"
                            except (RuntimeError, subprocess.TimeoutExpired) as exc:
                                errors.append(f"page {i+1}: {str(exc)[:200]}")
                        page_records.append({"n": i + 1, "t": text if mode != "empty" else "", "mode": mode})
                record = {"version": VERSION, "id": ident, "sha256": digest,
                          "ocr_attempted": args.ocr == "auto", "pages": page_records, "errors": errors}
                write_json(dest, record)
            except Exception as exc:
                issues.append(f"{d['path']}: {exc}")
                stats["failed_documents"] += 1
                continue
        native = sum(p["mode"] == "text" for p in record["pages"])
        recognized = sum(p["mode"] == "ocr" for p in record["pages"])
        empty = len(record["pages"]) - native - recognized
        coverage.append({"id": ident, "path": d["path"], "pages": len(record["pages"]),
                         "native_pages": native, "ocr_pages": recognized, "scan_only_pages": empty})
        stats["documents"] += 1
        stats["pages"] += len(record["pages"])
        stats["native_pages"] += native
        stats["ocr_pages"] += recognized
        stats["scan_only_pages"] += empty
        for page in record["pages"]:
            if page["t"]:
                rows.append({"d": ident, "p": page["n"], "t": page["t"], "kind": page["mode"]})
                present_pages.add((ident, page["n"]))
        issues.extend(f"{d['path']}: {s}" for s in record.get("errors", []))
        print(f"[{n:02}/{len(pdfs)}] {ident} {source.name}: {native} text / {recognized} OCR / {empty} scan-only", flush=True)
    if stats["failed_documents"]:
        sys.exit("Some PDFs could not be read; published chunks were not replaced.\n" + "\n".join(issues))
    stats["text_pages"] = stats["native_pages"] + stats["ocr_pages"]
    excerpt_file = site / "reviewed-excerpts.json"
    if excerpt_file.exists():
        excerpts = json.loads(excerpt_file.read_text(encoding="utf-8"))
        by_id = {d["id"]: d for d in catalog}
        for excerpt in excerpts:
            if excerpt["d"] not in by_id:
                continue
            if (excerpt["d"], excerpt["p"]) not in present_pages:
                rows.append({"d": excerpt["d"], "p": excerpt["p"], "t": excerpt["t"], "kind": "reviewed_excerpt"})
                stats["reviewed_excerpts"] += 1
    rows.sort(key=lambda item: (item["d"], item["p"], item["kind"]))
    chunks, pending, size = [], [], 0
    def flush() -> None:
        nonlocal pending, size
        if pending:
            name = f"chunk-{len(chunks):04d}.json"
            write_json(out / name, pending)
            chunks.append(name)
            pending, size = [], 0
    for row in rows:
        row_size = len(json.dumps(row, ensure_ascii=False).encode("utf-8"))
        if pending and size + row_size > CHUNK_BYTES:
            flush()
        pending.append(row)
        size += row_size
    flush()
    for old in out.glob("chunk-*.json"):
        if old.name not in chunks:
            old.unlink()
    for old in cache.glob("*.json"):
        if old.name not in active_cache:
            old.unlink()
    manifest = {"version": VERSION, "stats": stats, "chunks": chunks,
                "documents": coverage, "warnings": issues,
                "coverage_note": "Native PDF text plus labeled reviewed excerpts. Scan-only counts include blank/low-text pages. Original files are unchanged."}
    write_json(out / "manifest.json", manifest)
    print("INDEX COMPLETE:", json.dumps(stats), f"in {len(chunks)} chunks", flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
