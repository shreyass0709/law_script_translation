"""LoRA fine-tune IndicTrans2 (English -> Kannada or Konkani) on our legal pairs.

Run from the repo root on a GPU machine:
    python training/train_lora.py --lang kn data/processed/constitution_train_kn.csv data/processed/anuvaad_legal_kn.csv
    python training/train_lora.py --lang kok data/processed/constitution_train_kok.csv
CSVs need an `en` column and `kn` (Kannada) or `kok_deva` (Konkani, Devanagari) column.
Saves the LoRA adapter to models/lora-<lang>/ (git-ignored). Use it with LORA_ADAPTER=models/lora-kn
for translate.py, evaluate.py and the API. Add --steps 2 for a quick smoke test.
"""
import argparse
import csv
import random
import sys
import time
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

sys.path.insert(0, "backend")
from indic_processor import IndicProcessor  # noqa: E402
from translate import LANGS, MODEL, REVISION, SRC  # noqa: E402

COLUMN = {"kn": "kn", "kok": "kok_deva"}

ap = argparse.ArgumentParser()
ap.add_argument("csvs", nargs="+")
ap.add_argument("--lang", choices=COLUMN, required=True)
ap.add_argument("--model", default=MODEL, help="e.g. ai4bharat/indictrans2-en-indic-1B on a big GPU")
ap.add_argument("--revision", default=None, help="model commit; defaults to the pinned one for the 200M model")
ap.add_argument("--epochs", type=int, default=5)
ap.add_argument("--batch", type=int, default=16)
ap.add_argument("--lr", type=float, default=2e-4)
ap.add_argument("--rank", type=int, default=16)
ap.add_argument("--steps", type=int, default=0, help="stop after this many steps (smoke test)")
ap.add_argument("--out", default=None)
args = ap.parse_args()
sys.stdout.reconfigure(encoding="utf-8")

tgt_lang, col = LANGS[args.lang], COLUMN[args.lang]
out = Path(args.out or f"models/lora-{args.lang}")
revision = args.revision or (REVISION if args.model == MODEL else None)
device = "cuda" if torch.cuda.is_available() else "cpu"
torch.manual_seed(0)
random.seed(0)

pairs = []
for path in args.csvs:
    pairs += [(r["en"], r[col]) for r in csv.DictReader(open(path, encoding="utf-8-sig")) if r["en"] and r[col]]
# Never train on test sentences, whatever file they arrive in.
norm = lambda s: " ".join(s.lower().split())  # noqa: E731
test = set()
for path in Path("data/processed").glob("*test*.csv"):
    test |= {norm(r["en"]) for r in csv.DictReader(open(path, encoding="utf-8-sig"))}
before = len(pairs)
pairs = list({norm(e): (e, t) for e, t in pairs if norm(e) not in test}.values())  # also dedups
print(f"{before} pairs read, {before - len(pairs)} dropped as duplicates or test sentences")
random.shuffle(pairs)
n_dev = max(20, len(pairs) // 20)  # 5% held out to watch for overfitting
dev, train = pairs[:n_dev], pairs[n_dev:]
print(f"{len(train)} train / {len(dev)} dev pairs, device {device}")

tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True, revision=revision)
model = AutoModelForSeq2SeqLM.from_pretrained(args.model, trust_remote_code=True, revision=revision)
# Same as AI4Bharat's LoRA recipe: attention projections only.
model = get_peft_model(model, LoraConfig(r=args.rank, lora_alpha=2 * args.rank, lora_dropout=0.1,
                                         target_modules=["q_proj", "k_proj", "v_proj", "out_proj"]))
model.print_trainable_parameters()
model.to(device)
# Training mode: no placeholders, so the model learns to copy numbers itself as well.
ip = IndicProcessor(inference=False)


def encode(batch):
    src = ip.preprocess_batch([e for e, _ in batch], src_lang=SRC, tgt_lang=tgt_lang)
    tgt = ip.preprocess_batch([t for _, t in batch], src_lang=tgt_lang, tgt_lang=SRC, is_target=True)
    enc = tok(src, text_target=tgt, truncation=True, max_length=256, padding="longest", return_tensors="pt")
    enc["labels"][enc["labels"] == tok.pad_token_id] = -100  # no loss on padding
    return enc.to(device)


def dev_loss():
    model.eval()
    total = 0.0
    with torch.no_grad(), torch.autocast(device, enabled=device == "cuda"):
        for i in range(0, len(dev), args.batch):
            total += model(**encode(dev[i:i + args.batch])).loss.item() * len(dev[i:i + args.batch])
    model.train()
    return total / len(dev)


opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr)
scaler = torch.amp.GradScaler(enabled=device == "cuda")
best, step = dev_loss(), 0
print(f"dev loss before training: {best:.3f}")
model.train()
for epoch in range(1, args.epochs + 1):
    random.shuffle(train)
    t0 = time.time()
    for i in range(0, len(train), args.batch):
        with torch.autocast(device, enabled=device == "cuda"):
            loss = model(**encode(train[i:i + args.batch])).loss
        scaler.scale(loss).backward()
        scaler.unscale_(opt)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(opt)
        scaler.update()
        opt.zero_grad()
        step += 1
        if step % 50 == 0:
            print(f"  step {step} loss {loss.item():.3f}", flush=True)
        if args.steps and step >= args.steps:
            break
    loss_now = dev_loss()
    print(f"epoch {epoch}: dev loss {loss_now:.3f} ({time.time() - t0:.0f}s)", flush=True)
    if loss_now < best:  # keep only the best epoch
        best = loss_now
        model.save_pretrained(out)
        print(f"  saved to {out}")
    if args.steps and step >= args.steps:
        break
if not out.exists():
    print("dev loss never improved; nothing saved (try a lower --lr)")
