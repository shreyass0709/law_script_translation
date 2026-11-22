"""Build English / Kannada pairs from Acts in data/raw/:
- `*KA.pdf` / `*_both.pdf`: both languages in one PDF, e.g. PRS India gazette copies of Karnataka
  Acts (Kannada pages, then English) or a page-by-page diglot (evidence_both.pdf).
- `<name>_e.pdf` + `<name>_k.pdf` (or `_english` / `_kannada`): one Act as two PDFs, e.g. a Central
  Act from India Code and its Kannada translation.

English text layers are clean; Kannada ones use legacy font encodings (Nudi etc., garbage as text),
so Kannada pages are always OCR'd. Units are matched by section / sub-section number across the Act.
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
PAIR = {"_e": "_k", "_english": "_kannada"}
# English Central Acts open with a table of contents whose numbered titles would collide with the
# sections; the body starts after the enactment date line, e.g. "[23rd May, 1986.]".
EN_FOOTNOTE = re.compile(r"(?m)^\s*\d{1,3}\.\s.*(?:\bby Act\b|\bw\.e\.f\b|\bSubs\.|\bIns\.|\b[Oo]mitted\b|\bRep\.|\bvide\b|\bibid\b|\bAdded by\b).*$")
ENACTED = re.compile(r"\[\d{1,2}(?:st|nd|rd|th)?\s+\w+,?\s*\d{4}\.?\]")


def pages(pdf: str) -> tuple[list[int], list[int]]:
    """(Kannada pages, English pages) of a one-PDF diglot, by which script dominates the text layer."""
    kn, en = [], []
    for i, page in enumerate(pymupdf.open(RAW / pdf)):
        t = page.get_text()
        k, e = len(KN.findall(t)), sum(c.isascii() and c.isalpha() for c in t)
        nudi = sum(0x80 <= ord(c) <= 0xFF for c in t)  # Nudi-font Kannada reads as Latin-1 junk: C¢ü¤AiÀÄªÀÄ
        if (k > e and k > 100) or (nudi > 30 and nudi > 0.05 * e):
            kn.append(i)
        elif e > 100:
            en.append(i)
    return kn, en


def sources() -> list[tuple]:
    """(name, Kannada pdf, its pages, English pdf, its pages or None for the whole file)."""
    out = []
    for path in sorted([*RAW.glob("*KA.pdf"), *RAW.glob("*_both.pdf")]):
        kn, en = pages(path.name)
        out.append((path.name, path.name, kn, path.name, en))
    for en_suf, kn_suf in PAIR.items():
        for path in sorted(RAW.glob(f"*{en_suf}.pdf")):
            kn_pdf = path.name[: -len(en_suf) - 4] + kn_suf + ".pdf"
            if (RAW / kn_pdf).exists():
                n = pymupdf.open(RAW / kn_pdf).page_count
                out.append((path.name, kn_pdf, list(range(n)), path.name, None))
    return out


def english(pdf: str, page_list) -> str:
    doc = pymupdf.open(RAW / pdf)
    if page_list is not None:
        return "\n".join(doc[p].get_text() for p in page_list)
    text = "\n".join(page.get_text() for page in doc)
    m = ENACTED.search(text)
    text = text[m.end():] if m else text
    # India Code footnotes ("1. Subs. by Act 34 of 2019, s. 95") reuse section numbers; drop them.
    return EN_FOOTNOTE.sub("", text)


def main():
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    tests = {r["en"] for f in OUT.glob("*test*.csv") if not f.name.startswith("acts_")
             for r in csv.DictReader(open(f, encoding="utf-8-sig"))}
    rows, seen = [], set()
    for name, kn_pdf, kn_pages, en_pdf, en_pages in sources():
        todo = [p for p in kn_pages if f"{kn_pdf}:{p}" not in cache]
        for i in range(0, len(todo), 40):  # save every 40 pages so a crash loses little
            batch = todo[i:i + 40]
            with ThreadPoolExecutor(4) as ex:
                for p, text in zip(batch, ex.map(lambda p: ocr_page(kn_pdf, p, "kan+eng"), batch)):
                    cache[f"{kn_pdf}:{p}"] = text
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            print(f"  {kn_pdf}: OCR {i + len(batch)}/{len(todo)}", flush=True)
        u_en = units(english(en_pdf, en_pages))
        u_kn = units("\n".join(cache[f"{kn_pdf}:{p}"] for p in kn_pages))
        n = 0
        for key in sorted(u_en.keys() & u_kn.keys() - {"head"}, key=str):
            # OCR reads anusvara as Kannada zero: ಒ೦ದು -> ಒಂದು
            e, k = u_en[key], re.sub(r"(?<=[ಅ-ೌ])೦", "ಂ", u_kn[key]).replace("ಂಂ", "ಂ")
            ratio = len(k) / max(len(e), 1)
            if (20 <= len(e) <= 600 and 0.7 <= ratio <= 1.6 and not FOOTNOTE.search(e)
                    and len(KN.findall(k)) > len(k) / 3 and e not in tests and e not in seen):
                seen.add(e)
                rows.append({"act": name, "key": ".".join(filter(None, key)), "en": e, "kn": k})
                n += 1
        print(f"{name}: {len(kn_pages)} Kannada pages, {len(u_en)}/{len(u_kn)} units -> {n} pairs", flush=True)
    for fname, part in [("acts_kn.csv", [r for r in rows if r["act"] != TEST_ACT]),
                        ("acts_test_kn.csv", [r for r in rows if r["act"] == TEST_ACT])]:
        with open(OUT / fname, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, ["act", "key", "en", "kn"])
            w.writeheader()
            w.writerows(part)
        print(f"{fname}: {len(part)} rows")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
