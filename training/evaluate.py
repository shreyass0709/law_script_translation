"""Score the baseline translator against data/processed/constitution_test.csv (chrF++ and BLEU).

Run from the repo root:  python training/evaluate.py
Konkani references are Devanagari; they are converted to Kannada script like the model output.
Scores are only as good as the OCR'd references: rows are reviewed=no until a native speaker checks them.
"""
import csv
import sys

import sacrebleu
from aksharamukha import transliterate

sys.path.insert(0, "backend")
from translate import translate  # noqa: E402

rows = list(csv.DictReader(open("data/processed/constitution_test.csv", encoding="utf-8-sig")))
src = [r["en"] for r in rows]
refs = {
    "kn": [r["kn"] for r in rows],
    "kok": [transliterate.process("Devanagari", "Kannada", r["kok_deva"]) for r in rows],
}
sys.stdout.reconfigure(encoding="utf-8")
print(f"{len(rows)} test sentences")
for lang, ref in refs.items():
    hyp = [h for i in range(0, len(src), 8) for h in translate(src[i:i + 8], lang)]
    chrf = sacrebleu.corpus_chrf(hyp, [ref], word_order=2)  # word_order=2 -> chrF++
    # Kannada/Konkani are agglutinative, so BLEU is harsh; chrF++ is the main number.
    bleu = sacrebleu.corpus_bleu(hyp, [ref], tokenize="none")
    print(f"{lang}: chrF++ {chrf.score:.1f}   BLEU {bleu.score:.1f}")
