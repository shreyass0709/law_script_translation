"""Build English / Kannada training pairs from the Constitution diglot (data/raw/kannada.pdf).

Uses every page EXCEPT the test-set pages (articles 12-100, see build_testset.py), so no test
text leaks into training. In the diglot each English page is followed by its Kannada page;
units are aligned per page by their article / clause number.
Run from the repo root:  python training/build_trainset.py
Writes data/processed/constitution_train_kn.csv. OCR shares the cache with build_testset.py.
"""
import csv
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor

from build_testset import CACHE, DIGLOT_PAGES, OUT, ocr_page

# Pages 60-67 (articles 1-11) and 170-798 (article 101 to the schedules).
PAGES = [p for p in range(60, 798) if p not in DIGLOT_PAGES]
assert PAGES[::2] == [p for p in PAGES if p % 2 == 0]  # English page even, its Kannada page next

# Article suffix letters as the Kannada text writes them: 243G -> 243ಜಿ.
KN_LETTER = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                     "ಎ ಬಿ ಸಿ ಡಿ ಇ ಎಫ್ ಜಿ ಎಚ್ ಐ ಜೆ ಕೆ ಎಲ್ ಎಂ ಎನ್ ಒ ಪಿ ಕ್ಯೂ ಆರ್ ಎಸ್ ಟಿ ಯು ವಿ ಡಬ್ಲ್ಯು ಎಕ್ಸ್ ವೈ ಜೆಡ್".split()))
MARK = re.compile(r"(?m)^\s*(?:(\d{1,3})([A-Z]{0,2}|[ಀ-೿]{0,8})\.\s*(?=\D)|\((\d{1,2})\)\s)")
FURNITURE = re.compile(r"(?m)^.*(?:The Constitution of India|ಭಾರತದ ಸಂವಿಧಾನ).*$")
FOOTNOTE = re.compile(r"\b(?:Subs\.|Ins\.|Omitted|w\.e\.f|Amendment\) Act|Rep\. by)", re.I)


def ocr_all() -> dict:
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    todo = [(f"kannada.pdf:{p}", p, "eng" if p % 2 == 0 else "kan+eng")
            for p in PAGES if f"kannada.pdf:{p}" not in cache]
    for i in range(0, len(todo), 40):  # save every 40 pages so a crash loses little
        batch = todo[i:i + 40]
        with ThreadPoolExecutor(4) as ex:
            for (key, *_), text in zip(batch, ex.map(lambda j: ocr_page("kannada.pdf", j[1], j[2]), batch)):
                cache[key] = text
        CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        print(f"OCR {min(i + 40, len(todo))}/{len(todo)}", flush=True)
    return cache


def units(text: str) -> dict:
    """{key: text} for one page. Key = (article, clause) of the marker that starts the unit;
    the text before the first marker (continued from the last page) gets key 'head'."""
    text = FURNITURE.sub("", text).replace("‌", "").replace("‍", "")
    text = re.sub(r"\d*\[|\]", "", text)  # amendment brackets: 1[text] -> text
    out, keys, art = {}, [], None
    pieces = MARK.split(text)
    head, rest = pieces[0], pieces[1:]
    out["head"] = head
    for num, suf, clause, body in zip(rest[0::4], rest[1::4], rest[2::4], rest[3::4]):
        if num:
            suf = "".join(KN_LETTER.get(c, c) for c in suf)
            art, key = num + suf, (num + suf, None)
        else:
            key = (art, clause)
        keys.append(key)
        out[key] = body
    dup = {k for k in keys if keys.count(k) > 1}
    return {k: " ".join(v.split()) for k, v in out.items() if k not in dup}


def main():
    cache = ocr_all()
    test_en = set()
    if (OUT / "constitution_test.csv").exists():
        test_en = {r["en"] for r in csv.DictReader(open(OUT / "constitution_test.csv", encoding="utf-8-sig"))}
    rows, seen = [], set()
    for p in PAGES[::2]:
        u_en, u_kn = units(cache[f"kannada.pdf:{p}"]), units(cache[f"kannada.pdf:{p + 1}"])
        for key in u_en.keys() & u_kn.keys():
            e, k = u_en[key], u_kn[key]
            ratio = len(k) / max(len(e), 1)
            if (20 <= len(e) <= 600 and 0.75 <= ratio <= 1.6 and not FOOTNOTE.search(e)
                    and len(re.findall(r"[ಀ-೿]", k)) > len(k) / 3
                    and e not in test_en and e not in seen):
                seen.add(e)
                rows.append({"page": p, "key": key if key == "head" else ".".join(filter(None, key)),
                             "en": e, "kn": k})
    with open(OUT / "constitution_train_kn.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, ["page", "key", "en", "kn"])
        w.writeheader()
        w.writerows(rows)
    print(f"page pairs: {len(PAGES) // 2}; rows written: {len(rows)}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
