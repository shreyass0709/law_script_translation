"""Score the translator against data/processed/constitution_test.csv: chrF++, BLEU and glossary accuracy.

Run from the repo root:  python training/evaluate.py
Konkani references are Devanagari; they are converted to Kannada script like the model output.
Scores are only as good as the OCR'd references: rows are reviewed=no until a native speaker checks them.
"""
import csv
import sys

import sacrebleu
from aksharamukha import transliterate

sys.path.insert(0, "backend")
import glossary  # noqa: E402
from segment import segment  # noqa: E402
from translate import translate  # noqa: E402

rows = list(csv.DictReader(open("data/processed/constitution_test.csv", encoding="utf-8-sig")))
src = [r["en"] for r in rows]
refs = {
    "kn": [r["kn"] for r in rows],
    "kok": [transliterate.process("Devanagari", "Kannada", r["kok_deva"]) for r in rows],
}
sys.stdout.reconfigure(encoding="utf-8")


def _term_rate(sources, outputs, lang):
    """Share of glossary terms in the source whose approved translation appears in the output."""
    checks = [t for s, o in zip(sources, outputs) for t in glossary.check(s, o, lang)]
    return f"{sum(t['found'] for t in checks)}/{len(checks)} ({100 * sum(t['found'] for t in checks) / max(len(checks), 1):.0f}%)"


print(f"{len(rows)} test sentences")
for lang, ref in refs.items():
    # Same path as the API: segment each row, translate the pieces, join them back.
    segs = [segment(s) for s in src]
    flat = translate([p for parts in segs for p in parts], lang)
    hyp, i = [], 0
    for parts in segs:
        hyp.append(" ".join(flat[i:i + len(parts)]))
        i += len(parts)
    chrf = sacrebleu.corpus_chrf(hyp, [ref], word_order=2)  # word_order=2 -> chrF++
    # Kannada/Konkani are agglutinative, so BLEU is harsh; chrF++ is the main number.
    bleu = sacrebleu.corpus_bleu(hyp, [ref], tokenize="none")
    print(f"{lang}: chrF++ {chrf.score:.1f}   BLEU {bleu.score:.1f}   "
          f"glossary terms used: {_term_rate(src, hyp, lang)}   (official reference: {_term_rate(src, ref, lang)})")
