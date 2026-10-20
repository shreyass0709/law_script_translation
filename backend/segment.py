"""Preprocessing: clean pasted/PDF legal text and cut it into model-sized segments.

Run `python backend/segment.py` for the self-check.
"""
import re

# A new segment starts at a section number, a (1)/(a)/(iv) marker, a proviso or an explanation.
_MARKER = r"(?:\d+[A-Z]?\.\s|\((?:\d+[A-Z]?|[a-z]{1,2}|[ivxlc]{1,6})\)\s|Provided\b|Explanation\b|Illustrations?\b)"
_LINE_START = re.compile(rf"\n\s*(?={_MARKER})")
# Inline clauses: "...namely:— (a) ...; (b) ..." start a segment after ; : or a dash,
# and a proviso or explanation starts one after a full stop.
_INLINE = re.compile(
    rf"(?:(?<=[;:—–-])|(?<=[;:] or)|(?<=[;:] and))\s+(?={_MARKER})"
    r"|(?<=\.)\s+(?=(?:Provided|Explanation|Illustrations?)\b)"
)
_SENTENCE = re.compile(r"(?<=[.?!])\s+(?=[A-Z“\"(])")
# Abbreviations, and a bare section number ("378.") before its heading.
_ABBREV = re.compile(r"(?:\b(?:No|Nos|Rs|Sec|Secs|Art|Arts|Cl|viz|i\.e|e\.g|etc|Govt|Dept|Ltd|Co|Mr|Mrs|Dr|St|[A-Z])|^\d+[A-Z]?)\.$")
# Split only near the model's 256-token limit (~1,000 chars), at ; or : and then sentences.
# Measured: splitting at 300 chars lowered Kannada chrF++; whole sentences translate better.
MAX_CHARS = 600


def clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("­", "")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # hyphenated PDF line breaks
    text = _LINE_START.sub("\n\n", text)  # a structure marker always starts a paragraph
    paras = re.split(r"\n\s*\n", text)
    return "\n\n".join(" ".join(p.split()) for p in paras if p.strip())


def _sentences(text: str) -> list[str]:
    out = []
    for part in _SENTENCE.split(text):
        if out and _ABBREV.search(out[-1]):  # "Rs. 5,000", "No. 12": not a sentence end
            out[-1] += " " + part
        else:
            out.append(part)
    return out


def _split_long(seg: str) -> list[str]:
    if len(seg) <= MAX_CHARS:
        return [seg]
    pieces = [p for p in re.split(r"(?<=[;:])\s+", seg) if p]
    # ponytail: a piece still over MAX_CHARS with no ; or : stays whole (the model truncates
    # at 256 tokens, roughly 1,000 characters). Split at commas if real acts hit this.
    return [s for p in pieces for s in (_sentences(p) if len(p) > MAX_CHARS else [p])]


def segment(text: str) -> list[str]:
    """Cleaned text -> ordered segments: one per section, sub-section, clause or proviso."""
    # Sentences are split only when a segment is too long: measured on the Constitution test
    # set, splitting every sentence lowered Kannada chrF++ by ~2.6.
    segs = []
    for para in clean(text).split("\n\n"):
        for part in _INLINE.split(para):
            segs += _split_long(part)
    return [s.strip() for s in segs if s.strip()]


if __name__ == "__main__":
    sample = (
        "378. Theft.—Whoever, intending to take dishonestly any moveable property out of the posses-\n"
        "sion of any person without that person's consent, moves that property, is said to commit theft.\n"
        "Explanation 1.—A thing so long as it is attached to the earth, not being moveable property, "
        "is not the subject of theft.\n\n"
        "(2) The State shall make no law: (a) taking away the right; or (b) abridging it, and a fine of "
        "Rs. 5,000 may be imposed. Provided that nothing here applies to Art. 21A."
    )
    segs = segment(sample)
    for s in segs:
        print(repr(s))
    assert segs[0].startswith("378. Theft.") and "possession" in segs[0], "hyphen join / section"
    assert segs[1].startswith("Explanation 1."), "explanation starts a segment"
    assert segs[2] == "(2) The State shall make no law:", segs[2]
    assert segs[3] == "(a) taking away the right; or", segs[3]
    assert segs[4].startswith("(b) abridging it") and "Rs. 5,000 may be imposed." in segs[4], "abbrev kept"
    assert segs[5] == "Provided that nothing here applies to Art. 21A.", segs[5]
    long = "; ".join(["the State shall not deny any person equality before the law"] * 8) + "."
    assert all(len(s) <= MAX_CHARS for s in segment(long)), "long segment split at ;"
    print("OK")
