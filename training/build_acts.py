"""Build English / Kannada pairs from Karnataka Acts that print both languages in one PDF
(PRS India gazette copies, e.g. data/raw/Act16of2024KA.pdf: Kannada pages, then English pages).

The English text layer is clean; the Kannada one uses a legacy font encoding (garbage), so
Kannada pages are OCR'd. Units are matched by section / sub-section number across the Act.
Run from the repo root:  python training/build_acts.py
Writes data/processed/acts_kn.csv (training) and acts_test_kn.csv (TEST_ACT, held out as a second
test set: `python training/evaluate.py --test data/processed/acts_test_kn.csv`).
OCR shares the cache with build_testset.py.
"""
import csv
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import pymupdf

from build_testset import CACHE, OUT, RAW, ocr_page
from build_trainset import FOOTNOTE, units

KN = re.compile(r"[ಀ-೿]")
TEST_ACT = "Act5of2024KA.pdf"  # held out: never trained on (train_lora drops *test*.csv text)


def pages(pdf: str) -> tuple[list[int], list[int]]:
    """(Kannada pages, English pages) by which script dominates the text layer."""
    kn, en = [], []
    for i, page in enumerate(pymupdf.open(RAW / pdf)):
        t = page.get_text()
        k, e = len(KN.findall(t)), sum(c.isascii() and c.isalpha() for c in t)
        if k > e and k > 100:
            kn.append(i)
        elif e > 100:
            en.append(i)
    return kn, en


def main():
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    tests = {r["en"] for f in OUT.glob("*test*.csv") if not f.name.startswith("acts_") for r in csv.DictReader(open(f, encoding="utf-8-sig"))}
    rows, seen = [], set()
    for path in sorted(RAW.glob("*KA.pdf")):
        pdf = path.name
        kn_pages, en_pages = pages(pdf)
        todo = [p for p in kn_pages if f"{pdf}:{p}" not in cache]
        with ThreadPoolExecutor(4) as ex:
            for p, text in zip(todo, ex.map(lambda p: ocr_page(pdf, p, "kan+eng"), todo)):
                cache[f"{pdf}:{p}"] = text
        CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        doc = pymupdf.open(path)
        u_en = units("\n".join(doc[p].get_text() for p in en_pages))
        u_kn = units("\n".join(cache[f"{pdf}:{p}"] for p in kn_pages))
        n = 0
        for key in sorted(u_en.keys() & u_kn.keys() - {"head"}, key=str):
            e, k = u_en[key], re.sub(r"(?<=[ಅ-ೌ])೦", "ಂ", u_kn[key]).replace("ಂಂ", "ಂ")  # OCR reads anusvara as zero
            ratio = len(k) / max(len(e), 1)
            if (20 <= len(e) <= 600 and 0.7 <= ratio <= 1.6 and not FOOTNOTE.search(e)
                    and len(KN.findall(k)) > len(k) / 3 and e not in tests and e not in seen):
                seen.add(e)
                rows.append({"act": pdf, "key": ".".join(filter(None, key)), "en": e, "kn": k})
                n += 1
        print(f"{pdf}: {len(kn_pages)} Kannada / {len(en_pages)} English pages -> {n} pairs", flush=True)
    for name, part in [("acts_kn.csv", [r for r in rows if r["act"] != TEST_ACT]),
                       ("acts_test_kn.csv", [r for r in rows if r["act"] == TEST_ACT])]:
        with open(OUT / name, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, ["act", "key", "en", "kn"])
            w.writeheader()
            w.writerows(part)
        print(f"{name}: {len(part)} rows")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
