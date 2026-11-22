"""Clean the Anuvaad legal-terms 2021 English/Kannada pairs (Supreme Court case headers, names).

Get the folder (legal-terms.en / legal-terms.kn) from the shared data drive, then run from the repo root:
    python training/clean_anuvaad.py <folder>
Writes data/processed/anuvaad_legal_kn.csv. Drops case-only duplicates and lines with no Kannada.
Known issue kept as-is: "Special Leave Petition" is translated ವಿಶೇಷ ರಜೆ ಅರ್ಜಿ ("leave" as holiday).
"""
import csv
import re
import sys
from pathlib import Path


def lines(path: Path) -> list[str]:
    # split on "\n" only: the .kn file has CRLF endings plus stray "\r" inside some lines
    with open(path, encoding="utf-8", newline="") as f:
        return [s.replace("\r", " ") for s in f.read().rstrip("\r\n").split("\n")]


src = Path(sys.argv[1])
en, kn = lines(src / "legal-terms.en"), lines(src / "legal-terms.kn")
assert len(en) == len(kn), "files are not line-aligned"

rows, seen = [], set()
for e, k in zip(en, kn):
    e, k = " ".join(e.split()), " ".join(k.split())
    if e.lower() in seen or not re.search(r"[ಀ-೿]", k):
        continue
    seen.add(e.lower())
    rows.append({"en": e, "kn": k})

out = Path("data/processed/anuvaad_legal_kn.csv")
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, ["en", "kn"])
    w.writeheader()
    w.writerows(rows)
print(f"{len(en)} lines in, {len(rows)} rows written to {out}")
