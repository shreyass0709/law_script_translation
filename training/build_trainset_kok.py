"""Build English / Konkani (Devanagari) training pairs from the Constitution PDFs.

konkani.pdf has no English, so units are matched by article number across the whole text
(English from the diglot pages OCR'd by build_trainset.py). Test articles 12-100 are skipped.
Run from the repo root, after build_trainset.py:  python training/build_trainset_kok.py
Writes data/processed/constitution_train_kok.csv. OCR shares the cache with the other builders.
"""
import csv
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor

from build_testset import CACHE, OUT, clauses, ocr_page, strip_heading

KOK_PAGES = range(40, 411)  # article 1 starts on page 40
EN_PAGES = range(60, 798, 2)  # English pages of the diglot
TEST = range(12, 101)
# Article suffixes in the Konkani text follow Devanagari alphabet order: 243A -> 243क, 243ZA -> 243यक.
DEVA = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "कखगघङचछजझञटठडढणतथदधनपफबभमय"))
FOOTNOTE = re.compile(r"\b(?:Subs\.|Ins\.|Omitted|w\.e\.f|Amendment\) Act|Rep\. by)", re.I)


def ocr_konkani() -> dict:
    cache = json.loads(CACHE.read_text(encoding="utf-8"))
    todo = [p for p in KOK_PAGES if f"konkani.pdf:{p}" not in cache]
    for i in range(0, len(todo), 40):
        batch = todo[i:i + 40]
        with ThreadPoolExecutor(4) as ex:
            for p, text in zip(batch, ex.map(lambda p: ocr_page("konkani.pdf", p, "mar+hin"), batch)):
                cache[f"konkani.pdf:{p}"] = text
        CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        print(f"OCR {min(i + 40, len(todo))}/{len(todo)}", flush=True)
    return cache


def articles(text: str, suffix: str) -> dict:
    """{'243छ': body} in rising article order, so footnotes and schedule entries are skipped."""
    found, last = {}, 0
    parts = re.split(rf"(?m)^\s*\[?(\d{{1,3}}{suffix})\.\s*(?=\D)", text)
    for key, body in zip(parts[1::2], parts[2::2]):
        n = int(re.match(r"\d+", key).group())
        if key not in found and last <= n <= last + 10:
            found[key], last = body, n
    return found


def main():
    cache = ocr_konkani()
    en = articles("\n".join(cache[f"kannada.pdf:{p}"] for p in EN_PAGES), "[A-Z]{0,2}")
    en = {re.sub(r"[A-Z]", lambda m: DEVA[m.group()], k): v for k, v in en.items()}
    kok = articles("\n".join(cache[f"konkani.pdf:{p}"] for p in KOK_PAGES), "[क-य]{0,2}")
    rows = []
    for key in en.keys() & kok.keys():
        if int(re.match(r"\d+", key).group()) in TEST:
            continue
        c_en, c_kok = clauses(strip_heading(en[key])), clauses(strip_heading(kok[key]))
        if len(c_en) != len(c_kok):
            continue
        for i, (e, k) in enumerate(zip(c_en, c_kok), 1):
            e = re.sub(r"\d*\[|\]", "", e)
            k = re.sub(r"\d*\[|\]", "", k)
            if (20 <= len(e) <= 600 and 0.7 <= len(k) / len(e) <= 1.5 and not FOOTNOTE.search(e)
                    and len(re.findall(r"[ऀ-ॿ]", k)) > len(k) / 3):
                rows.append({"article": key + (f".{i}" if len(c_en) > 1 else ""), "en": e, "kok_deva": k})
    with open(OUT / "constitution_train_kok.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, ["article", "en", "kok_deva"])
        w.writeheader()
        w.writerows(rows)
    print(f"articles: en={len(en)} kok={len(kok)} common={len(en.keys() & kok.keys())}; rows written: {len(rows)}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
