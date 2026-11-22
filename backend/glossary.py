"""Legal glossary: find English legal terms in a segment and check the translation uses the
approved Kannada / Konkani term. data/glossary/legal_terms.csv is the source of truth.

Run `python backend/glossary.py` for the self-check.
"""
import csv
import re
from functools import lru_cache
from pathlib import Path

from aksharamukha import transliterate

GLOSSARY = Path(__file__).resolve().parent.parent / "data" / "glossary" / "legal_terms.csv"
# A trailing vowel sign changes with case suffixes (ಸಂಸತ್ತು -> ಸಂಸತ್ತಿನ), so match without it.
_MATRA = re.compile(r"[ಾ-ೌ]$")


@lru_cache(maxsize=1)
def _terms() -> list[dict]:
    rows = list(csv.DictReader(open(GLOSSARY, encoding="utf-8")))
    for r in rows:
        r["kok"] = transliterate.process("Devanagari", "Kannada", r["kok_deva"])  # output script
        flags = re.I if r["en"].islower() else 0  # "Act" and "Bill" only when capitalised
        r["pattern"] = re.compile(rf"\b{re.escape(r['en'])}(?:s|es)?\b", flags)
    return sorted(rows, key=lambda r: len(r["en"]), reverse=True)  # longest first


def entries(lang: str) -> list[dict]:
    """The term list for the UI: [{en, target}] in Kannada script."""
    return [{"en": r["en"], "target": r[lang]} for r in sorted(_terms(), key=lambda r: r["en"].lower())]


def find_terms(source: str) -> list[dict]:
    """Glossary terms in an English segment, longest match first ("Supreme Court" before "court")."""
    taken, found = [], []
    for r in _terms():
        for m in r["pattern"].finditer(source):
            if not any(m.start() < e and s < m.end() for s, e in taken):
                taken.append((m.start(), m.end()))
                if r not in found:
                    found.append(r)
    return found


def check(source: str, translation: str, lang: str) -> list[dict]:
    """[{en, target, found}] for each glossary term in the source. found=False -> needs review."""
    return [
        {"en": r["en"], "target": r[lang], "found": _MATRA.sub("", r[lang]) in translation}
        for r in find_terms(source)
    ]


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    assert [r["en"] for r in find_terms("The Supreme Court may hear any court matter.")] == ["Supreme Court", "court"]
    assert [r["en"] for r in find_terms("Parliament may by law amend this article.")] == ["Parliament", "article", "law"]
    assert [r["en"] for r in find_terms("sub-section (2) of section 4")] == ["sub-section", "section"]
    assert find_terms("He did not act on the bill.") == [], "lowercase act/bill are not the Act/Bill"
    ok = check("Nothing in this article applies.", "ಈ ಅನುಚ್ಛೇದದಲ್ಲಿರುವ ಯಾವುದೂ ಅನ್ವಯಿಸುವುದಿಲ್ಲ.", "kn")
    bad = check("Nothing in this article applies.", "ಈ ಲೇಖನದಲ್ಲಿರುವ ಯಾವುದೂ ಅನ್ವಯಿಸುವುದಿಲ್ಲ.", "kn")
    assert ok == [{"en": "article", "target": "ಅನುಚ್ಛೇದ", "found": True}], ok
    assert bad[0]["found"] is False
    assert check("an Act of Parliament", "ಸಂಸತ್ತಿನ ಅಧಿನಿಯಮ", "kn")[1]["found"], "suffix form ಸಂಸತ್ತಿನ matches"
    assert check("the President", "ರಾಷ್ಟ್ರಪತೀಂಚೆ", "kok")[0]["found"], "Konkani compared in Kannada script"
    print("OK")
