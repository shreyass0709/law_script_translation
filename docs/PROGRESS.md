# Progress log

Shared team memory. Read the top before you start; add an entry in every PR.
Newest entry first.

## Current status

- **Sprint:** 1 (baseline) — done: model, API and web page work end to end
- **Next up:** test sentences + starter glossary, then Sprint 2 (segmentation, number protection)

## Owners

| Area | Owner |
|------|-------|
| Data & glossary | Shashank G Suvarna |
| Preprocessing | Srajan D Prabhu |
| Model & evaluation | Shridhar V Kamath |
| API & frontend | Shreyas S |

## Open decisions

- Where large data/model files live (shared Drive vs. Hugging Face) — add the link here.

## Decisions made

- 2026-10-08 — Target languages are **Kannada and Konkani only**. Tulu dropped from scope.
- 2026-10-08 — Base model: AI4Bharat IndicTrans2 (`kan_Knda`, `gom_Deva`). Start with the
  distilled 200M model, move to 1B on GPU if quality needs it.
- 2026-10-08 — Backend in Python (FastAPI). No database or login in v1.
- 2026-10-08 — Konkani is shown in **Kannada script**: model outputs Devanagari, pipeline
  converts the script with a library. Confirmed by the guide.
- 2026-10-08 — Frontend is **Next.js**; backend stays Python.

## Log

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
