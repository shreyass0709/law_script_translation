"""Baseline translation: English -> Kannada / Konkani with IndicTrans2.

Run `python backend/translate.py` to translate the sample sections and
self-check the output scripts.
"""
import sys
from functools import lru_cache

import torch
from aksharamukha import transliterate
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from indic_processor import IndicProcessor

MODEL = "ai4bharat/indictrans2-en-indic-dist-200M"
# The model repo ships Python code that runs on load; pin the commit we have tested.
REVISION = "2cfd0a20057756d756bf3e53528f492afc52f91a"
SRC = "eng_Latn"
# Our language codes -> IndicTrans2 codes. Konkani only exists in Devanagari in the model.
LANGS = {"kn": "kan_Knda", "kok": "gom_Deva"}
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


@lru_cache(maxsize=1)
def _load():
    kwargs = {"trust_remote_code": True, "revision": REVISION}
    tokenizer = AutoTokenizer.from_pretrained(MODEL, **kwargs)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL, **kwargs).to(DEVICE).eval()
    return tokenizer, model, IndicProcessor(inference=True)


def translate(sentences: list[str], lang: str) -> list[str]:
    """Translate English sentences. lang is "kn" or "kok"; both come back in Kannada script."""
    tgt = LANGS[lang]
    tokenizer, model, ip = _load()
    batch = ip.preprocess_batch(sentences, src_lang=SRC, tgt_lang=tgt)
    inputs = tokenizer(batch, truncation=True, padding="longest", return_tensors="pt").to(DEVICE)
    with torch.no_grad():
        # ponytail: one batch, 256-token cap. Long sections get truncated until the
        # preprocessing module (Sprint 2) splits them into sentence-sized segments.
        out = model.generate(**inputs, max_length=256, num_beams=5)
    decoded = tokenizer.batch_decode(out, skip_special_tokens=True, clean_up_tokenization_spaces=True)
    result = ip.postprocess_batch(decoded, lang=tgt)
    if lang == "kok":
        result = [transliterate.process("Devanagari", "Kannada", s) for s in result]
    return result


SAMPLES = [
    "No person shall be deprived of his life or personal liberty except according to procedure established by law.",
    "Whoever, intending to take dishonestly any moveable property out of the possession of any person "
    "without that person's consent, moves that property in order to such taking, is said to commit theft.",
]


def _in_block(text: str, lo: int, hi: int) -> bool:
    return any(lo <= ord(c) <= hi for c in text)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"device: {DEVICE}")
    for lang in LANGS:
        outputs = translate(SAMPLES, lang)
        for src, out in zip(SAMPLES, outputs):
            print(f"\n[en]  {src}\n[{lang}] {out}")
            assert _in_block(out, 0x0C80, 0x0CFF), f"{lang}: no Kannada-script characters"
            assert not _in_block(out, 0x0900, 0x097F), f"{lang}: Devanagari left in output"
    print("\nOK")
