# Architecture

## 1. What we are building

Input: English legal text (pasted, or extracted from a PDF/TXT upload).
Output: the same text in **Kannada** or **Konkani**, shown side by side with the
source, with legal terms translated consistently and numbering/citations intact.

From the synopsis, the five objectives are:

1. Automated English → regional-language legal translation.
2. NLP translation models that handle legal terminology, structure and context.
3. A legal text preprocessing module (tokenization, normalization, legal-term identification).
4. A user-friendly interface with target-language selection.
5. Evaluation and validation of the output for semantic consistency.

Each objective maps to a module below.

## 2. Languages

| Language | Script | IndicTrans2 code | Notes |
|----------|--------|------------------|-------|
| English (source) | Latin | `eng_Latn` | |
| Kannada | Kannada | `kan_Knda` | Well resourced; fine-tuning is realistic |
| Konkani | Kannada (converted from Devanagari) | `gom_Deva` | Low resource; very little legal parallel data |

**Konkani script: Kannada script (decided 2026-10-08).** The model can only
produce Konkani in Devanagari (the official script, used in Goa). Konkani in
coastal Karnataka is written in Kannada script, so the pipeline converts the
model output with a rule-based Devanagari → Kannada script conversion (script
only, the words do not change). Use an existing library for this
(`aksharamukha` or `indic-transliteration`), not hand-written rules. The
Devanagari text is the intermediate result, so offering it as a second view
costs nothing. Konkani-specific spellings (nasal vowels, nukta letters) need
checking by a Konkani speaker — keep a small list of test words.

## 3. Pipeline

```
          ┌────────────┐
 text/PDF │  Frontend  │  language picker, side-by-side view, download
 ────────►│  (web UI)  │
          └─────┬──────┘
                │ POST /translate {text, target_lang}
          ┌─────▼──────────────────────────────────────────────┐
          │ Backend API (FastAPI)                               │
          │                                                     │
          │ 1. Ingest        PDF/TXT → raw text                 │
          │ 2. Preprocess    clean, normalize, segment          │
          │ 3. Protect       mask numbers, citations, glossary  │
          │ 4. Translate     IndicTrans2 (batch of sentences)   │
          │ 5. Postprocess   unmask, apply glossary, rebuild    │
          │ 6. Konkani only  Devanagari → Kannada script        │
          └─────┬───────────────────────────────────────────────┘
                │ {segments: [{source, translation, terms}]}
                ▼
            Frontend renders aligned source/target segments
```

Offline, separate from the request path:

```
 Data collection → parallel corpus + glossary → fine-tune (Kannada) → evaluate → report
```

## 4. Modules

### 4.1 Ingest
- Plain text straight through. PDF via `pypdf` text extraction.
- Scanned (image) PDFs are out of scope for v1 — no OCR.

### 4.2 Preprocessing (objective 3)
- **Clean**: fix PDF line breaks and hyphenation, collapse whitespace, strip page headers/footers.
- **Segment by legal structure**: section → sub-section `(1)` → clause `(a)` → proviso
  ("Provided that…") → explanation. Keep the hierarchy so output can be rebuilt in the same shape.
- **Sentence split** long sub-sections on `;` / `:` / proviso boundaries. Legal sentences
  are far longer than the model's comfortable length, and quality drops on long inputs.
- **Identify legal terms** by matching against the glossary (longest match first).

### 4.3 Protection (mask before translating)
Things that must come out unchanged are replaced by placeholders, then restored:
- Section/article/clause numbers: `Section 302`, `Article 21`, `(2)(b)`
- Citations and act names with year: `Indian Penal Code, 1860`
- Dates, amounts, percentages
- Latin maxims and terms the glossary marks "do not translate"

### 4.4 Translation (objective 2)
- **Model: IndicTrans2** by AI4Bharat (open source, MIT licence, covers both languages).
  - Start: `ai4bharat/indictrans2-en-indic-dist-200M` — small, runs on a laptop CPU.
  - Better quality: `ai4bharat/indictrans2-en-indic-1B` — needs a GPU (Colab T4 is enough).
- Loaded once at server start via Hugging Face `transformers` + `IndicTransToolkit`.
- **Kannada**: fine-tune with LoRA on legal parallel data (section 5), compare against the baseline.
- **Konkani**: baseline model + glossary enforcement. Fine-tune only if enough parallel data is found.
- Why not a general tool (Google Translate, an LLM API): the synopsis is specifically about a
  *domain-specific* model; those are used only as comparison baselines in evaluation.

### 4.5 Postprocessing
- Restore placeholders.
- **Glossary enforcement**: for every English legal term found in the source, check the
  approved target term is in the output; if not, flag the segment (and replace where safe).
- Rebuild numbering and indentation from the segment hierarchy.

### 4.6 Backend API
- **FastAPI** (Python, same language as the model code).
- `POST /translate` — `{text, target_lang: "kn" | "kok"}` → aligned segments.
- `POST /translate/file` — PDF/TXT upload, same response.
- `GET /glossary?lang=` — the term list, for the UI to highlight terms.
- No database and no login in v1. Add only if the guide asks for history/accounts.

### 4.7 Frontend (objective 4)
- Web UI: text box / file upload, language selector (Kannada, Konkani), translate button.
- Side-by-side source and translation, aligned per segment; legal terms highlighted with
  the glossary meaning on hover; flagged segments marked "needs review".
- Copy and download (TXT) of the result. Visible "not a certified translation" disclaimer.
- Stack: **Next.js (React), decided 2026-10-08.** Chosen over Streamlit because the UI needs
  segment-aligned columns, per-term hover highlights and review flags, which Streamlit
  handles poorly. Only the frontend owner needs to know React; everyone else works in Python.

### 4.8 Evaluation (objective 5)
- **Automatic**: BLEU and chrF++ with `sacrebleu` on a held-out legal test set per language.
- **Comparison table** for the report: baseline IndicTrans2 vs. fine-tuned vs. + glossary
  (and a general-purpose translator as an outside reference).
- **Glossary accuracy**: % of legal terms rendered with the approved term.
- **Human review**: native speakers on the team rate a sample (adequacy and fluency, 1–5).
  Konkani leans mostly on this because reference translations are scarce.

## 5. Data

| Need | Candidate sources | Status |
|------|-------------------|--------|
| English–Kannada legal parallel text | India Code (central acts with Kannada versions); Karnataka state acts published in both languages (DPAL Karnataka) | to collect |
| English–Kannada general parallel text | AI4Bharat Samanantar / BPCC | available |
| English–Konkani parallel text | BPCC (general); Goa government gazette / official Konkani publications | to investigate — expect very little legal text |
| Legal glossary EN→KN | Karnataka government legal/administrative glossaries (Kannada Development Authority, Law Dept.) | to source |
| Legal glossary EN→KOK | Goa official language resources; otherwise built by hand with a Konkani speaker | to build |
| Test sets | ~200–300 sentence pairs per language, held out, never trained on | to build |

Rules: datasets do not go in git (see `.gitignore`). Keep them on a shared Drive or a
Hugging Face dataset repo and record the link in `PROGRESS.md`. The glossary
(`data/glossary/*.csv`, small) **does** go in git — it is the team's core asset.

Check the licence/terms of every source before using it, and note it in `PROGRESS.md`.

## 6. Repository layout (target)

```
backend/
  app/            FastAPI app, routes
  pipeline/       ingest, preprocess, protect, translate, postprocess
  tests/
frontend/         web UI
data/
  glossary/       en-kn.csv, en-kok.csv   (in git)
  raw/ processed/                          (NOT in git)
training/         fine-tuning + evaluation notebooks/scripts
docs/             ARCHITECTURE.md, PROGRESS.md
```

Folders are created when the first real file goes in, not before.

## 7. Roadmap (sprints, per the Agile methodology in the synopsis)

| Sprint | Goal | Done when |
|--------|------|-----------|
| 0 | Repo, docs, everyone can clone and push | all 4 members have merged one PR |
| 1 | Baseline end to end | paste English text → get Kannada and Konkani from baseline IndicTrans2 via API + bare UI |
| 2 | Preprocessing + protection | section numbers/citations survive; long sections are segmented and rebuilt |
| 3 | Glossary | EN→KN and EN→KOK glossaries (first 200+ terms), enforcement + UI highlighting |
| 4 | Data + fine-tuning (Kannada) | legal parallel corpus built, LoRA fine-tune run, numbers vs. baseline |
| 5 | Evaluation | test sets, BLEU/chrF++ table, human review scores for both languages |
| 6 | Polish | PDF upload, download, error handling, demo script, report and paper figures |

Sprint 1 comes first on purpose: a working baseline early means every later
sprint is a measurable improvement rather than a guess.

## 8. Suggested work split

| Owner | Area | Covers |
|-------|------|--------|
| A | Data & glossary | sources, parallel corpus, glossaries, test sets |
| B | Preprocessing | ingest, cleaning, segmentation, protection, postprocessing |
| C | Model & evaluation | IndicTrans2 serving, fine-tuning, metrics |
| D | API & frontend | FastAPI routes, web UI, integration |

Assign real names in `PROGRESS.md`. At least one Kannada and one Konkani speaker
should own human review for that language.

## 9. Known limits (state these in the report)

- Machine output is not legally certified; human verification is required for official use.
- Konkani quality is bounded by scarce data; results will be weaker than Kannada.
- No OCR; scanned PDFs are unsupported.
- Very long documents are slow on CPU; the demo should use section-sized inputs or a GPU.
