"""Build a small English / Kannada / Konkani test set from the official Constitution PDFs.

Needs Tesseract + the kan/mar/hin/eng language data (see docs/PROGRESS.md) and these files
in data/raw/ (git-ignored): kannada.pdf (English/Kannada diglot), konkani.pdf (Devanagari).
Run from the repo root:  python training/build_testset.py
Writes data/processed/constitution_test.csv. OCR is cached in data/processed/ocr_cache.json.
Rows are machine-read (OCR): a native speaker must spot-check them (reviewed=no).
"""
import csv
import io
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image

os.environ.setdefault("TESSDATA_PREFIX", str(Path.home() / ".tessdata"))
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

RAW, OUT = Path("data/raw"), Path("data/processed")
CACHE = OUT / "ocr_cache.json"
# 0-based pages: Part III (Fundamental Rights) and the start of Part IV, articles 12-100.
# In the diglot an English page is followed by its Kannada page.
DIGLOT_PAGES = range(68, 170)
KONKANI_PAGES = range(44, 100)
FIRST, LAST = 12, 100
DASH = r"[\u2014\u2013\u2015-]+"


def ocr_page(pdf: str, page: int, lang: str) -> str:
    pix = pymupdf.open(RAW / pdf)[page].get_pixmap(dpi=250)
    return pytesseract.image_to_string(Image.open(io.BytesIO(pix.tobytes("png"))), lang=lang, config="--psm 6")


def ocr_all() -> dict:
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    jobs = []
    for p in DIGLOT_PAGES:
        lang = "eng" if (p - DIGLOT_PAGES[0]) % 2 == 0 else "kan+eng"
        jobs.append((f"kannada.pdf:{p}", "kannada.pdf", p, lang))
    jobs += [(f"konkani.pdf:{p}", "konkani.pdf", p, "mar+hin") for p in KONKANI_PAGES]
    todo = [j for j in jobs if j[0] not in cache]
    with ThreadPoolExecutor(4) as ex:
        for (key, *_), text in zip(todo, ex.map(lambda j: ocr_page(*j[1:]), todo)):
            cache[key] = text
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return cache


def articles(text: str) -> dict:
    """Split running text into {article number: body}, keeping the numbers in rising order."""
    found, last = {}, FIRST - 1
    parts = re.split(r"(?m)^\s*\[?(\d{1,3}[A-Z]?)\.\s", text)
    for num, body in zip(parts[1::2], parts[2::2]):
        n = int(re.match(r"\d+", num).group())
        if num not in found and last < n <= LAST and (n - last <= 3 or not found):
            found[num], last = body, n
    return found


def strip_heading(body: str) -> str:
    """Drop page furniture and the article heading ('Equality before law.-')."""
    body = re.sub(r"(?m)^.*(?:The Constitution of India|ಭಾರತದ ಸಂವಿಧಾನ|भारताचें संविधान).*$", "", body)
    body = re.sub(r"(?m)^\s*(?:PART|ಭಾಗ|\(?भाग)\b.*$", "", body)
    body = " ".join(body.split())
    return re.sub(rf"^.*?{DASH}\s*", "", body, count=1)


def clauses(text: str) -> list[str]:
    """['(1) a', '(2) b'] for an article with numbered clauses, else [whole text]."""
    parts = re.split(r"(?=\(\d+\)\s)", text)
    return [p.strip() for p in parts if p.strip()]


def main():
    cache = ocr_all()
    en = "\n".join(cache[f"kannada.pdf:{p}"] for p in DIGLOT_PAGES[0::2])
    kn = "\n".join(cache[f"kannada.pdf:{p}"] for p in DIGLOT_PAGES[1::2])
    kok = "\n".join(cache[f"konkani.pdf:{p}"] for p in KONKANI_PAGES)
    A_en, A_kn, A_kok = articles(en), articles(kn), articles(kok)
    rows = []
    for num in A_en:
        if num not in A_kn or num not in A_kok:
            continue
        raw = A_en[num]
        if re.search(r"\d\[|\bSubs\.|\bIns\.|\bOmitted\b", raw):  # amended text + footnotes
            continue
        c_en, c_kn, c_kok = (clauses(strip_heading(a[num])) for a in (A_en, A_kn, A_kok))
        if not (len(c_en) == len(c_kn) == len(c_kok)):
            continue
        for i, (e, k, o) in enumerate(zip(c_en, c_kn, c_kok), 1):
            if 40 <= len(e) <= 450:
                rows.append({"id": f"art{num}" + (f".{i}" if len(c_en) > 1 else ""),
                             "en": e, "kn": k, "kok_deva": o, "reviewed": "no"})
    with open(OUT / "constitution_test.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, ["id", "en", "kn", "kok_deva", "reviewed"])
        w.writeheader()
        w.writerows(rows)
    print(f"articles found: en={len(A_en)} kn={len(A_kn)} kok={len(A_kok)}; rows written: {len(rows)}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
