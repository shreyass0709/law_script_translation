# Progress log

Shared team memory. Read the top before you start; add an entry in every PR.
Newest entry first.

## Current status

- **Sprint:** 4 (data + fine-tuning) — in progress. Sprint 3 (glossary, 59 terms) done.
  Shreyas is working on it alone for now.
- **Next up:** first LoRA run on the college GPU (`training/train_lora.py`, steps in the README);
  more Kannada legal pairs (Central Acts). Native-speaker check of the test set and the glossary still pending.

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

### 2026-11-23 — Karnataka Acts: second test set
- PRS India's gazette copies of Karnataka Acts hold both languages in one PDF (Kannada pages, then
  English). `training/build_acts.py` reads the English text layer, OCRs the Kannada pages (their text
  layer is a legacy font encoding, unusable) and matches by section / sub-section number. Fixes the
  OCR reading anusvara as Kannada zero (ಒ೦ದು → ಒಂದು). PDFs go in `data/raw/` as `*KA.pdf`.
- 9 Acts (PDFs in `data/raw/`, git-ignored): Karnataka Acts 16/2024 (76 pairs), 5/2024 (71), 41/2025 and
  8/2024 (3; only a 2-page Kannada notice) from PRS India; Central Acts with their Kannada translations:
  Motor Vehicles 1988 (313), Evidence 1872 (50, page-by-page diglot `evidence_both.pdf`), Environment
  Protection 1986 (27), Hindu Marriage 1955 (25), RTI 2005 (11). Separate-file Acts are named
  `<name>_e.pdf` / `<name>_k.pdf` (or `_english` / `_kannada`); India Code footnotes are stripped
  because their numbers collide with section numbers. Spot checks of 12 rows were all correct pairs.
- **Act 5 of 2024 is held out** as a second test set, `acts_test_kn.csv` (71 rows); never trained on.
  The other **505 pairs** go in `acts_kn.csv` (added to the README training command).
- E0 baseline on the Act test set: Kannada chrF++ **61.0**, BLEU 18.6, glossary 85%, references kept 94%.
- The `A*.pdf` India Code files in `data/raw/` are English only and unused. Low yields (RTI, Evidence)
  are from sections whose numbering differs between the files; page-by-page pairing of the Evidence
  diglot could recover more if needed.

### 2026-11-23 — native-speaker review sheets
- `python training/review_sheets.py export` writes `data/processed/review_kn.xlsx` and `review_kok.xlsx`
  (git-ignored): an instructions sheet, then one row per test sentence with an OK/FIX dropdown and a
  "Corrected text" column. The Konkani sheet also shows the text in Kannada script for easier reading.
- When they come back: `python training/review_sheets.py import <file(s)>` copies fixes into
  `constitution_test.csv` and sets `reviewed=yes` on rows checked in both languages. Re-run
  `evaluate.py` afterwards; the E0 numbers become final.

### 2026-11-22 — PDF upload, download, and a decoding fix
- `POST /extract` takes PDF bytes as the request body and returns the text (pymupdf, now a main
  dependency). Limits: 10 MB; PDFs without an English text layer (scanned) get a 422 with a clear
  message, since there is no OCR. The page has an "Upload a PDF" button that fills the text box
  (cut to 20,000 characters with a notice), a "Download translation (.txt)" button (disclaimer
  included), and shows the API's own error messages.
- **Bug fixed in `translate.py`:** beam search without `early_stopping` let padded batches of short
  segments (a PDF's table of contents) run on to 256 tokens of "....", about 50 s per batch, so the
  website's proxy timed out. With `early_stopping=True` a 3-page PDF (90 segments) translates in about
  11 s. It also raised the baseline; the E0 table in the next entry has the new numbers.
- Checked end to end through the website: upload → extract → translate (both languages), non-PDF
  → 400, blank PDF → 422; `backend/test_api.py` covers the same.

### 2026-11-22 — evaluation: legal metrics in one command
- `training/evaluate.py` now also reports **references kept** (numbers, sections, citations and dates
  from the source that appear unchanged in the output) and takes `--test <csv>` / `--lang`, so the
  held-out Act test set can be scored the same way. With `LORA_ADAPTER` set it scores the fine-tuned model.
- E0 baseline (200M, no fine-tuning, with the `early_stopping` fix), 49-sentence Constitution test
  set, provisional until reviewed. Compare every fine-tuned run against this:

  | | chrF++ | BLEU | Glossary terms used | References kept |
  |---|---|---|---|---|
  | Kannada | 52.6 | 14.5 | 75% (98/131) | 93% (42/45) |
  | Konkani | 41.5 | 8.6 | 60% (79/131) | 100% (45/45) |

  The official translations keep only 89% of references by this check because they write some in
  Kannada letters (21A → 21ಎ); that is a style difference, not an error.

### 2026-11-22 — Sprint 4: first Kannada training data
- `training/build_trainset.py` builds **840 English/Kannada pairs** from the Constitution diglot
  (`kannada.pdf`): every page except the test pages (68-169, articles 12-100), so no test text leaks
  in. Each English page is paired with the Kannada page after it, and units are matched by article
  and clause number; pairs with odd length ratios or amendment footnotes are dropped. Output:
  `data/processed/constitution_train_kn.csv` (git-ignored). A 10-row sample was all correct pairs,
  with small OCR letter slips.
- `training/clean_anuvaad.py` cleans the Anuvaad legal-terms 2021 set (3,356 lines → **1,843 pairs**,
  case-only duplicates removed): short Supreme Court case headers and names, useful for numbers and
  citations. Known bad translation: "Special Leave Petition" → ವಿಶೇಷ ರಜೆ ಅರ್ಜಿ ("leave" as holiday).
- Checked and **not used** for fine-tuning:
  - Samanantar Kannada (4.09M pairs): AI4Bharat's own data that IndicTrans2 was already trained on,
    mostly news, so it adds no legal skill. At most ~17k legal-looking rows could be mixed in.
  - A 70,157-row English/Konkani (Devanagari) Excel file: genuine Konkani but health/tourism text,
    header row missing, 57 duplicates. Keep it for later Konkani work.
- `training/build_trainset_kok.py` builds **275 English/Konkani pairs** from `konkani.pdf` (not a
  diglot, so articles are matched by number across the whole text; suffixes follow Devanagari order,
  243A = 243क). Test articles 12-100 skipped. Low count: many articles split into different clause
  counts in the two PDFs and are dropped. A 10-row sample was all correct pairs.
- `training/train_lora.py` LoRA-fine-tunes IndicTrans2 (attention projections, r=16, best epoch kept
  by dev loss on a 5% hold-out) and saves `models/lora-<lang>/`. `backend/translate.py` loads it when
  `LORA_ADAPTER` is set, so `evaluate.py` and the API use it unchanged. Target-side tokenisation was
  checked on this laptop, and a 2-step smoke test ran on the laptop GPU (RTX 3050 4 GB): dev loss 1.706 → 1.689, adapter saved and loaded by `translate.py`. Full runs are planned on the college GPU.
- ~2,700 Kannada / 275 Konkani pairs is small for LoRA. Next: more legal Kannada pairs (Kannada
  Central Acts on legislative.gov.in / India Code, Karnataka Gazette two-language Acts).
- `training/build_general_mix.py` samples general text to mix in (~15% of training) so general
  quality does not drop: `general_kn.csv` (500 from Samanantar) and `general_kok.csv` (300 from the
  Konkani Excel file). `train_lora.py` now drops any pair whose English is in a `*test*.csv` and
  removes duplicates; all current files had zero test overlap.
- Data sources checked online: **MILPaC has no Kannada** (9 other languages). No official Kannada BNS
  found. Under the Karnataka Official Language Act 1963 s.5A, Kannada translations of Central Acts are
  published by the Karnataka government (DPAL), so look there, and on India Code's Karnataka State Acts.
  legislative.gov.in, indiacode.nic.in and dpal.kar.nic.in refuse automated downloads: PDFs must be
  downloaded by hand in a browser into `data/raw/acts/`.
- Related work for the report: `law-ai/InLegalTrans-En2Indic-1B` (IndicTrans2 fine-tuned on MILPaC;
  no Kannada/Konkani), which our Kannada/Konkani legal model complements.

### 2026-10-20 — Sprint 3: legal glossary
- `data/glossary/legal_terms.csv`: 59 English terms with Kannada and Konkani (Devanagari) equivalents.
  Each was checked against the official Constitution text (OCR, articles 12-100): a term counts as
  found when the Kannada/Konkani word appears in the same articles as the English one. The
  `kn_evidence`/`kok_evidence` columns record the result. "section", "sub-section" and "imprisonment"
  are still "needs check": the Constitution barely uses them.
  Several first guesses were wrong and fixed from the text, for example Konkani "Provided that" = शर्त,
  "Explanation" = फोडणिशी, "Act" = अधिनेम; Kannada "Union" = ಒಕ್ಕೂಟ.
- `backend/glossary.py` finds terms in each English segment (longest match first) and checks that the
  translation contains the approved term (ignoring case endings). The API returns `terms` and
  `needs_review` per segment, and `GET /glossary?lang=` lists the terms. The page marks segments
  that miss a term.
- Flag only, no automatic replacement: Kannada/Konkani add case endings to words, so swapping
  words in the output is unsafe. Fine-tuning (Sprint 4) is the real fix.
- Glossary accuracy on the 49-sentence test set (approved term used / terms in source):

  | | Model | Official reference (same check) |
  |---|---|---|
  | Kannada | 76% (99/131) | 85% |
  | Konkani | 61% (80/131) | 89% |

  The reference column is a sanity check on the glossary itself; OCR slips and inflected forms keep it below 100%.
- Not done yet: the architecture's 200+ terms. Add terms to the CSV with evidence; a native speaker should review it.

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
