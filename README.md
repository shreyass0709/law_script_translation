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

### Run the API

```powershell
uvicorn api:app --app-dir backend
```

Open http://127.0.0.1:8000/docs and try `POST /translate` with
`{"text": "Section 302 ...", "target_lang": "kn"}` (or `"kok"`). The text is split into sections,
sub-sections, clauses and provisos (`backend/segment.py`); legal references such as `302(2)(b)`,
`21A` and `5,000` are kept unchanged.
`python backend\test_api.py` checks it end to end, including that numbers and dates survive.

### Run the website

Needs Node.js 20 or newer. Keep the API running in one PowerShell window, then in a second one:

```powershell
cd frontend
npm install      # first time only
npm run dev
```

Open http://localhost:3000, paste English text, pick Kannada or Konkani, and click Translate.
The page sends `/api/*` requests on to the API at `http://127.0.0.1:8000`; set `API_URL` to change that.

### Fine-tune on a GPU machine (e.g. the college GPU)

The training data is git-ignored, so copy it yourself (pen drive / Drive): **all** CSVs in
`data/processed/` (legal pairs, `general_*.csv` mix, and `constitution_test.csv` for scoring and
the leak check). On the GPU machine (Linux shown):

```bash
git clone https://github.com/shreyass0709/law_script_translation.git && cd law_script_translation
python -m venv ~/.venvs/lst && source ~/.venvs/lst/bin/activate
pip install torch                       # check `nvidia-smi`; pick the CUDA build from pytorch.org if needed
pip install -r backend/requirements.txt
hf auth login                           # your own Hugging Face token (see above)
mkdir -p data/processed                 # put the copied CSVs here

# 1. Smoke test (a minute): must print a dev loss and save models/lora-kn/
python training/train_lora.py --lang kn --steps 2 data/processed/constitution_train_kn.csv
# 2. Real run (Kannada): legal pairs + ~15% general text
python training/train_lora.py --lang kn data/processed/constitution_train_kn.csv data/processed/anuvaad_legal_kn.csv data/processed/general_kn.csv
#    Konkani: python training/train_lora.py --lang kok data/processed/constitution_train_kok.csv data/processed/general_kok.csv
# 3. Score it against the baseline
LORA_ADAPTER=models/lora-kn python training/evaluate.py
```

If loading fails with `not a valid model identifier` / `OAuth token has expired`, your Hugging Face
login is stale (with `peft` installed, transformers also checks the Hub for an adapter): run
`hf auth login` again, or set `HF_HUB_OFFLINE=1` when the model is already downloaded.

Bring back the `models/lora-kn/` folder (a few MB). Running the API with `LORA_ADAPTER=models/lora-kn`
set uses the fine-tuned model. Shared GPU servers often need jobs run inside `tmux` or `screen`
so they keep going after you log out.

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
