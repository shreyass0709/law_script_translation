# Progress log

Shared team memory. Read the top before you start; add an entry in every PR.
Newest entry first.

## Current status

- **Sprint:** 2 (preprocessing + protection) — done
- **Next up:** Sprint 3 — glossary (EN→KN, EN→KOK legal terms) and enforcement; native-speaker check of the test set

## Owners

| Area | Owner |
|------|-------|
| Data & glossary | Shashank G Suvarna |
| Preprocessing | Srajan D Prabhu |
| Model & evaluation | Shridhar V Kamath |
| API & frontend | Shreyas S |

## Open decisions

- Where large data/model files live (shared Drive vs. Hugging Face) — add the link here.
- Test set (`data/processed/constitution_test.csv`, git-ignored) is OCR'd and **not yet checked by a native speaker**; the scores below are provisional until it is.

## Decisions made

- 2026-10-08 — Target languages are **Kannada and Konkani only**. Tulu dropped from scope.
- 2026-10-08 — Base model: AI4Bharat IndicTrans2 (`kan_Knda`, `gom_Deva`). Start with the
  distilled 200M model, move to 1B on GPU if quality needs it.
- 2026-10-08 — Backend in Python (FastAPI). No database or login in v1.
- 2026-10-08 — Konkani is shown in **Kannada script**: model outputs Devanagari, pipeline
  converts the script with a library. Confirmed by the guide.
- 2026-10-08 — Frontend is **Next.js**; backend stays Python.

## Log

### 2026-10-20 — Sprint 2: segmentation and reference protection
- `backend/segment.py` cleans pasted/PDF text (joins wrapped lines and hyphenation) and splits it at
  sections, `(1)`/`(a)` markers, provisos and explanations. Segments over 600 characters are also
  split at `;`/`:` and sentences, so nothing reaches the model's 256-token limit.
- Reference protection reuses IndicTrans2's `<ID>` placeholders with one extra pattern in
  `backend/indic_processor.py`. Before, the model wrote `5, 000`, `21ಎ` and `(ಬಿ)`; now `5,000`,
  `21A` and `302(2)(b)` come out unchanged (checked in `backend/test_api.py`).
- Fixed two problems in the vendored processor: placeholders the model transliterated
  (`<ऐ. डि. 1>`) are now restored, and `ID1` no longer breaks `<ID10>`.
- Scores on the 49-sentence test set (chrF++ / BLEU):

  | | Baseline | Sprint 2 |
  |---|---|---|
  | Kannada | 52.8 / 14.8 | 52.0 / 14.9 |
  | Konkani | 39.1 / 8.3 | 38.6 / 8.5 |

  About level overall, but references are now exact. Two first attempts scored lower (47.8):
  masking every `(3)` cost ~4 points and splitting every sentence cost ~2.6, so both were narrowed.
- Known: with less context, "article" sometimes comes out as ಲೇಖನ instead of ಅನುಚ್ಛೇದ. That is the
  glossary's job (Sprint 3). Clause letters stay Latin `(b)`, while official Kannada texts write `(ಬಿ)`.
- The API input cap was raised to 20,000 characters.

### 2026-10-20 — baseline scores (provisional)
- Test set: 49 English sentences with official Kannada and Konkani text, Constitution articles
  12-100, from the government PDFs. Built by `training/build_testset.py`; scored by `training/evaluate.py`.
- Baseline (distilled 200M model, no glossary, no fine-tuning):

  | Language | chrF++ | BLEU |
  |----------|--------|------|
  | Kannada  | 52.8   | 14.8 |
  | Konkani (Kannada script) | 39.1 | 8.3 |

  Konkani references are Devanagari, converted to Kannada script the same way as the output.
- How the data was made: `kannada.pdf` (English/Kannada diglot) and `konkani.pdf` have broken text
  layers (legacy font encoding, swapped letters), so the pages are OCR'd with Tesseract
  (`kan`, `mar`, `hin`, `eng` data in `~/.tessdata`). The OCR text looked clean, but a few letters
  will be wrong. Only articles without amendment footnotes and with matching clause counts are kept.
- PDFs live in `data/raw/` (git-ignored). Get them from legislative.gov.in (Constitution in regional languages).
- Next: a Kannada and a Konkani speaker check the 49 rows (set `reviewed` to yes or fix them), then re-score.

### 2026-10-20 — web page
- Done: `frontend/`, a Next.js page with English text input, a Kannada/Konkani switch, and
  source-next-to-translation results. It shows the disclaimer at the top.
- The page sends `/api/*` requests on to FastAPI (`next.config.mjs`), so the backend needs no CORS setup.
- Run with `npm run dev` in `frontend/` while the API is running; see the README.
- Sprint 1 goal met: paste English, get Kannada and Konkani through the API and the UI.

### 2026-10-20 — translate API
- Done: `backend/api.py`, FastAPI `POST /translate` taking `{text, target_lang: "kn" | "kok"}` and
  returning `{segments: [{source, translation}], disclaimer}`. The model loads once at startup.
  Run with `uvicorn api:app --app-dir backend`; docs at `/docs`.
- `backend/test_api.py` checks the endpoint end to end: "Section 302", "15 August 2023" and
  "1950" come through unchanged in both languages.
- Limits for now: one segment per input line, input capped at 5000 characters. Sprint 2
  preprocessing replaces both. The code is flat in `backend/`, not the `backend/app/` layout in
  the architecture doc yet; move it when the pipeline modules arrive.
- Next: bare Next.js page with the disclaimer.

### 2026-10-08 — baseline translation works
- Done: `backend/translate.py` translates English into Kannada, and into Konkani converted to
  Kannada script (aksharamukha). Runs on GPU or CPU. Setup steps are in the README.
- Gotchas found:
  - The official `IndicTransToolkit` package needs a C compiler on Windows. We vendor its last
    pure-Python processor as `backend/indic_processor.py` instead.
  - `transformers` 5.x cannot load the model; pinned to 4.51.3.
  - The model is gated on Hugging Face: every member needs their own account, access and token.
- Not checked yet: translation quality. Native speakers must review the two sample outputs,
  and the Konkani spelling after script conversion.
- Next: API route, then the UI; in parallel start collecting the glossary and test sentences.

### 2026-10-08 — project setup
- Done: README, architecture doc, this log, CLAUDE.md, .gitignore.
- Next: each member clones, picks an area above, merges one small PR.
  Then Sprint 1: load IndicTrans2 and translate one hard-coded section into both languages.
