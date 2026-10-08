# Progress log

Shared team memory. Read the top before you start; add an entry in every PR.
Newest entry first.

## Current status

- **Sprint:** 0 (setup)
- **Next up:** Sprint 1 — baseline end to end (see `ARCHITECTURE.md` section 7)

## Owners

| Area | Owner |
|------|-------|
| Data & glossary | _unassigned_ |
| Preprocessing | _unassigned_ |
| Model & evaluation | _unassigned_ |
| API & frontend | _unassigned_ |

## Open decisions

- Where large data/model files live (shared Drive vs. Hugging Face) — add the link here.

## Decisions made

- 2026-10-08 — Target languages are **Kannada and Konkani only**. Tulu dropped from scope.
- 2026-10-08 — Base model: AI4Bharat IndicTrans2 (`kan_Knda`, `gom_Deva`). Start with the
  distilled 200M model, move to 1B on GPU if quality needs it.
- 2026-10-08 — Backend in Python (FastAPI). No database or login in v1.
- 2026-10-08 — Konkani is shown in **Kannada script**: model outputs Devanagari, pipeline
  converts the script with a library. Confirm with the guide; reversing it is one switch.
- 2026-10-08 — Frontend is **Next.js**; backend stays Python.

## Log

### 2026-10-08 — project setup
- Done: README, architecture doc, this log, CLAUDE.md, .gitignore.
- Next: each member clones, picks an area above, merges one small PR.
  Then Sprint 1: load IndicTrans2 and translate one hard-coded section into both languages.
