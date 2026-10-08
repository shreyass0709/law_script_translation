# Law Script Translation — project memory

Major project, team of 4 sharing this repo. English legal text → **Kannada** and
**Konkani** (Tulu is out of scope — do not add it).

## Read first
- `docs/PROGRESS.md` — current sprint, owners, open/made decisions, latest log entry.
- `docs/ARCHITECTURE.md` — pipeline, modules, data plan, roadmap. Follow it; if a change
  contradicts it, update the doc in the same PR.

## Keeping the team in sync
This repo is the shared memory: teammates work on other machines and cannot see
any local/personal Claude memory. Anything the next person needs to know goes in
`docs/PROGRESS.md` (status, decisions, links to data/models), committed and pushed.
After finishing a piece of work, add a dated entry to its Log section.

## Rules
- Work on a branch (`<area>/<short-name>`), merge to `main` by Pull Request.
- Never commit datasets, model weights, `.env`, or the synopsis PDF (it has student details).
  The glossary CSVs in `data/glossary/` are the exception and belong in git.
- Model: AI4Bharat IndicTrans2, codes `eng_Latn` → `kan_Knda` / `gom_Deva`.
- Numbers, section references, citations and dates must survive translation unchanged.
- Output is never presented as a certified legal translation; keep the disclaimer in the UI.
