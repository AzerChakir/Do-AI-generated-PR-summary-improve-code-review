#!/bin/bash
#SBATCH --account=def-<YOUR_ACCOUNT>
#SBATCH --output=logs/%A_%a.log
#SBATCH --error=logs/%A_%a.log
#SBATCH --nodes=1
#SBATCH --cpus-per-task=12
#SBATCH --mem=128G
#SBATCH --gpus-per-node=h100:4
#SBATCH --time=168:00:00
#SBATCH --job-name=crqa-large

# ── Environment setup ──────────────────────────────────────────────
module load StdEnv/2023 cuda/12 python/3.11 scipy-stack/2024a

VENV_DIR="$HOME/crqa-venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR ..."
    virtualenv --no-download "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install --no-index --upgrade pip
    pip install vllm==0.9.1 pandas tqdm
else
    source "$VENV_DIR/bin/activate"
fi

cd "$HOME/CodeReviewQA" || { echo "CodeReviewQA directory not found"; exit 1; }

mkdir -p logs results

# ── Run large models (≤72B, 4 GPUs) ───────────────────────────────
echo "=== Starting large tier run (4 GPUs) ==="
echo "Date: $(date)"
echo "Node: $(hostname)"
nvidia-smi

python main.py --tier large --results-dir results
