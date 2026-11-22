"""Score the translator on a test CSV: chrF++, BLEU, glossary accuracy and reference preservation.

Run from the repo root:  python training/evaluate.py [--test data/processed/constitution_test.csv] [--lang kn]
With LORA_ADAPTER=models/lora-kn set, the fine-tuned model is scored instead of the baseline.
The CSV needs `en` plus `kn` and/or `kok_deva`; languages without a column are skipped.
Konkani references are Devanagari; they are converted to Kannada script like the model output.
Scores are only as good as the OCR'd references: rows are reviewed=no until a native speaker checks them.
"""
import argparse
import csv
import re
import sys

import sacrebleu
from aksharamukha import transliterate

sys.path.insert(0, "backend")
import glossary  # noqa: E402
from segment import segment  # noqa: E402
from translate import translate  # noqa: E402

# Numbers, section/article references, citations and dates: 302(2)(b), 21A, 5,000, 15, 1950.
REF = re.compile(r"\d+(?:[.,/-]\d+)*[A-Z]{0,2}(?:\(\w{1,4}\))*")


def term_rate(sources, outputs, lang):
    """Share of glossary terms in the source whose approved translation appears in the output."""
    checks = [t for s, o in zip(sources, outputs) for t in glossary.check(s, o, lang)]
    ok = sum(t["found"] for t in checks)
    return f"{ok}/{len(checks)} ({100 * ok / max(len(checks), 1):.0f}%)"


def ref_rate(sources, outputs):
    """Share of references in the source that appear character-for-character in the output."""
    refs = [(r, o) for s, o in zip(sources, outputs) for r in REF.findall(s)]
    ok = sum(r in o for r, o in refs)
    return f"{ok}/{len(refs)} ({100 * ok / max(len(refs), 1):.0f}%)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", default="data/processed/constitution_test.csv")
    ap.add_argument("--lang", choices=["kn", "kok"], action="append", help="default: every language in the file")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    rows = list(csv.DictReader(open(args.test, encoding="utf-8-sig")))
    src = [r["en"] for r in rows]
    refs = {}
    if "kn" in rows[0]:
        refs["kn"] = [r["kn"] for r in rows]
    if "kok_deva" in rows[0]:
        refs["kok"] = [transliterate.process("Devanagari", "Kannada", r["kok_deva"]) for r in rows]
    print(f"{args.test}: {len(rows)} test sentences")
    for lang, ref in refs.items():
        if args.lang and lang not in args.lang:
            continue
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
        print(f"{lang}: chrF++ {chrf.score:.1f}   BLEU {bleu.score:.1f}")
        print(f"    glossary terms used: {term_rate(src, hyp, lang)}   (official reference: {term_rate(src, ref, lang)})")
        print(f"    references kept:     {ref_rate(src, hyp)}   (official reference: {ref_rate(src, ref)})")


if __name__ == "__main__":
    main()
