# Law Script Translation to Regional Languages

Major project (Team 9, Dept. of ISE). A domain-specific system that translates
**English legal text** (acts, sections, clauses, government notifications) into
**Kannada** and **Konkani**, preserving legal meaning.

> Scope note: only Kannada and Konkani. Tulu is **out of scope**.

## Where everything is

| File | What it is |
|------|------------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Full design: pipeline, modules, models, data, evaluation, roadmap, work split |
| [docs/PROGRESS.md](docs/PROGRESS.md) | Shared team log: what is done, what is next, decisions. **Update it in every PR.** |
| [CLAUDE.md](CLAUDE.md) | Project memory for Claude Code. Loaded automatically on every teammate's machine |

## Getting started (each teammate, once)

```bash
git clone https://github.com/shreyass0709/law_script_translation.git
cd law_script_translation
```

Then read `docs/ARCHITECTURE.md` and the top of `docs/PROGRESS.md`.

### Backend setup (Python 3.13, Windows PowerShell)

```powershell
# 1. Virtual environment. Keep it OUTSIDE OneDrive/Dropbox folders: it is several GB.
python -m venv $HOME\.venvs\law-script-translation
& $HOME\.venvs\law-script-translation\Scripts\Activate.ps1

# 2. PyTorch. With an NVIDIA GPU:
pip install torch --index-url https://download.pytorch.org/whl/cu124
#    Without one (slower, but works):
pip install torch

# 3. Everything else
pip install -r backend\requirements.txt
```

The model is access-restricted on Hugging Face, so each person does this once:

1. Create a free account at huggingface.co.
2. Open https://huggingface.co/ai4bharat/indictrans2-en-indic-dist-200M and accept the terms.
3. Create a **Read** token at https://huggingface.co/settings/tokens.
4. Run `hf auth login` and paste the token. Never commit or share the token.

Check it works (first run downloads the model, under 1 GB):

```powershell
$env:PYTHONIOENCODING = "utf-8"
python backend\translate.py
```

It prints two sample sections in Kannada and Konkani and ends with `OK`.

## Team workflow (4 people, one repo)

1. `git checkout main && git pull` before starting anything.
2. Create a branch per task: `git checkout -b <area>/<short-name>`
   (areas: `data`, `preprocess`, `model`, `eval`, `api`, `ui`, `docs`).
3. Commit small, push, open a Pull Request on GitHub, get one teammate to review, merge.
4. In the same PR, add a line to `docs/PROGRESS.md` (done / next / decisions).
5. Never commit model weights, datasets over a few MB, `.env` files, or the synopsis PDF.
   Large files go to shared Drive / Hugging Face; put the link in `docs/PROGRESS.md`.

## Disclaimer

Output is machine translation for legal awareness only. It is not a certified
legal translation and must be verified by a qualified person before any official use.
