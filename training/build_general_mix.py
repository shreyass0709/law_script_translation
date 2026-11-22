"""Sample a small general-text set to mix into LoRA training, so general quality does not drop.

Kannada from Samanantar (parquet files), Konkani from the English/Konkani Excel file a friend shared
(its first data row was read as the header, so it is read with header=None). Run from the repo root:
    python training/build_general_mix.py kn  <samanantar parquet files...> [--n 500]
    python training/build_general_mix.py kok <konkani_dataset.xlsx>        [--n 500]
Writes data/processed/general_<lang>.csv with columns en and kn / kok_deva.
Aim for about 15% of the training set: n ~= 0.18 x the number of legal pairs.
"""
import argparse
import csv
import re

import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("lang", choices=["kn", "kok"])
ap.add_argument("files", nargs="+")
ap.add_argument("--n", type=int, default=500)
args = ap.parse_args()

if args.lang == "kn":
    df = pd.concat(pd.read_parquet(f, columns=["src", "tgt"]) for f in args.files)
    col, script = "kn", r"[ಀ-೿]"
else:
    df = pd.read_excel(args.files[0], header=None, names=["src", "tgt"])
    col, script = "kok_deva", r"[ऀ-ॿ]"

df = df.dropna().astype(str)
df["src"], df["tgt"] = df.src.str.split().str.join(" "), df.tgt.str.split().str.join(" ")
ratio = df.tgt.str.len() / df.src.str.len()
df = df[df.src.str.len().between(30, 300) & ratio.between(0.6, 1.8)
        & df.tgt.str.contains(script) & ~df.src.str.contains(script)]
df = df.drop_duplicates("src")
sample = df.sample(min(args.n, len(df)), random_state=0)

out = f"data/processed/general_{args.lang}.csv"
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["en", col])
    w.writerows(sample[["src", "tgt"]].itertuples(index=False))
print(f"{len(df)} usable rows, {len(sample)} written to {out}")
