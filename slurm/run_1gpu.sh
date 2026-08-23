#!/bin/bash
#SBATCH --account=def-<YOUR_ACCOUNT>
#SBATCH --output=logs/%A_%a.log
#SBATCH --error=logs/%A_%a.log
#SBATCH --nodes=1
#SBATCH --cpus-per-task=12
#SBATCH --mem=32G
#SBATCH --gpus-per-node=h100:1
#SBATCH --time=48:00:00
#SBATCH --job-name=crqa-small

# ── Environment setup ──────────────────────────────────────────────
module load StdEnv/2023 cuda/12 python/3.11 scipy-stack/2024a

# ── Keep all caches off $HOME (tiny quota on Alliance) ─────────────
SCRATCH="${SCRATCH:-$HOME/scratch}"
export HF_HOME="$SCRATCH/hf/home"             # HF model weights / datasets
export VLLM_CACHE_ROOT="$SCRATCH/hf/vllm"     # vLLM torch.compile cache (fixes Errno 122)
export TRITON_CACHE_DIR="$SCRATCH/hf/triton"  # compiled Triton kernels
export TORCHINDUCTOR_CACHE_DIR="$SCRATCH/hf/inductor"
export PIP_CACHE_DIR="$SCRATCH/hf/pip"
mkdir -p "$HF_HOME" "$VLLM_CACHE_ROOT" "$TRITON_CACHE_DIR" "$TORCHINDUCTOR_CACHE_DIR" "$PIP_CACHE_DIR"

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

# ── Run small models (≤16B, 1 GPU) ────────────────────────────────
echo "=== Starting small tier run (1 GPU) ==="
echo "Date: $(date)"
echo "Node: $(hostname)"
nvidia-smi

python main.py --tier small --results-dir results
