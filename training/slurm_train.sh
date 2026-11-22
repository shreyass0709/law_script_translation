#!/bin/bash
# Slurm job for the NMAMIT H200 cluster: LoRA-train Kannada and Konkani, then score both.
# Submit from the repo folder on the cluster (never run training on the login node):
#   mkdir -p logs && sbatch training/slurm_train.sh
# Smoke test first (2 steps per language, a few minutes):
#   sbatch --export=ALL,STEPS=2 training/slurm_train.sh
#SBATCH --job-name=lora_legal
#SBATCH --partition=h200
#SBATCH --gres=gpu:1g.18gb:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=/home/%u/law_script_translation/logs/train_%j.log
set -euo pipefail

# %u only works in #SBATCH lines; use $HOME (absolute) below.
cd "$HOME/law_script_translation"
source "$HOME/env/bin/activate"
export HF_HOME="$HOME/law_script_translation/hf_cache"  # cluster rule: model cache inside the project
export PYTHONIOENCODING=utf-8
STEPS="${STEPS:-0}"
D=data/processed

echo "job ${SLURM_JOB_ID:-none}: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)"

python training/train_lora.py --lang kn --steps "$STEPS" \
  $D/constitution_train_kn.csv $D/anuvaad_legal_kn.csv $D/acts_kn.csv $D/general_kn.csv
python training/train_lora.py --lang kok --steps "$STEPS" \
  $D/constitution_train_kok.csv $D/general_kok.csv

echo "== Kannada, Constitution test (baseline chrF++ 52.6)"
LORA_ADAPTER=models/lora-kn python training/evaluate.py --lang kn
echo "== Kannada, Karnataka Act test (baseline chrF++ 61.0)"
LORA_ADAPTER=models/lora-kn python training/evaluate.py --test $D/acts_test_kn.csv
echo "== Konkani, Constitution test (baseline chrF++ 41.5)"
LORA_ADAPTER=models/lora-kok python training/evaluate.py --lang kok
echo "DONE"
