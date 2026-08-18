# CodeReviewQA: Evaluating LLM Code Review Comprehension with Summary-Augmented Prompting


## About

This project evaluates large language models on their ability to understand and resolve code review comments. It is built on top of the [CodeReviewQA benchmark](https://aclanthology.org/2025.findings-acl.476/) (Lin et al., ACL Findings 2025), which decomposes the generative task of automated code refinement (ACR) into three intermediate reasoning steps formulated as multiple-choice question answering (MCQA) probes.

This fork extends the original benchmark by introducing a **summary-augmented prompting** approach: before generating or answering, the model receives a structured natural-language summary of the code review intent alongside the original review comment. The goal is to measure whether providing an explicit summary improves model comprehension across the reasoning steps.

## The CodeReviewQA Benchmark

The original [CodeReviewQA benchmark](https://huggingface.co/datasets/Tomo-Melb/CodeReviewQA) consists of **900 manually curated code review examples** across **9 programming languages** (C, C++, CSharp, Go, Java, JavaScript, PHP, Python, Ruby). Each example is sourced from real GitHub code review interactions.

The benchmark evaluates four tasks:

| Task | Type | Description |
|------|------|-------------|
| **ACR** (Automated Code Refinement) | Generative | Generate the post-review code revision that addresses the review comment |
| **CTR** (Change Type Recognition) | MCQA | Infer whether the review asks to add, delete, or modify code |
| **CL** (Change Localisation) | MCQA | Locate the precise lines of code that need to be revised (easy/hard) |
| **SI** (Solution Identification) | MCQA | Identify the correct code revision among distractors (easy/hard) |

Each MCQA probe is evaluated under **invariance testing**: the model must select the correct answer for every permutation of the answer options, reducing the chance of random correct guesses.

## Summary-Augmented Prompting

The key extension in this project is the use of **code review summaries** as additional context in the prompts. Instead of providing only the raw review comment, the model also receives a structured summary that captures the reviewer's intent.

### Datasets

| Dataset | Use | Description |
|---------|-----|-------------|
| [Tomo-Melb/CodeReviewQA](https://huggingface.co/datasets/Tomo-Melb/CodeReviewQA) | Baseline (no summary) | Original benchmark with raw code review comments |
| [AzerChakir/CodeReviewWithSummaryQA](https://huggingface.co/datasets/AzerChakir/CodeReviewWithSummaryQA) | Summary approach | Same examples augmented with structured review summaries |

### Prompt Comparison

**Without summary** (default):
```
### The following Python code snippet has received a code review.
[Python]
<code>
[/Python]
[CODE REVIEW]
<review comment>
[/CODE REVIEW]
### Please generate a revised version ...
```

**With summary** (`--summary` flag):
```
### The following Python code snippet has received a code review.
[Python]
<code>
[/Python]
[CODE REVIEW]
<review comment>
[/CODE REVIEW]
[SUMMARY]
<intent summary>
[/SUMMARY]
### Please generate a revised version ...
```

The `--summary` / `--no-summary` flag controls which dataset and prompt template is used. By default, summary is ON.

## Running on Fir (Alliance Canada)

### Prerequisites

- Account on [Digital Research Alliance of Canada](https://www.alliancecan.ca/)
- Access to the **Fir** cluster (`fir.alliancecan.ca`)
- Hugging Face access token

### Setup

```bash
ssh fir.alliancecan.ca
git clone <your-repo-url> ~/CodeReviewQA
cd ~/CodeReviewQA

# Edit slurm/run_*.sh: replace def-<YOUR_ACCOUNT> with your sponsor's account
# Edit main.py: set HF_TOKEN to your Hugging Face token
```

### GPU Tiers

The benchmark includes 72 models ranging from 1B to 72B parameters. Three Slurm scripts handle the different GPU requirements:

| Script | Tier | Models | GPUs | Max Time |
|--------|------|--------|------|----------|
| `slurm/run_1gpu.sh` | small | 50 models (≤16B) | 1 x H100 | 48h |
| `slurm/run_2gpu.sh` | medium | 13 models (≤34B) | 2 x H100 | 72h |
| `slurm/run_4gpu.sh` | large | 9 models (≤72B) | 4 x H100 | 168h |

### Submitting Jobs

```bash
# Submit all tiers
sbatch slurm/run_1gpu.sh
sbatch slurm/run_2gpu.sh
sbatch slurm/run_4gpu.sh

# Or run a specific tier interactively
salloc --account=def-<YOUR_ACCOUNT> --gpus=h100:1 --mem=32G
python main.py --tier small

# Check job status
squeue -u $USER
```

### CLI Options

```
python main.py [OPTIONS]

Options:
  --tier {small,medium,large}  Run only models from a specific GPU tier
  --no-skip-existing          Re-run even if .pkl outputs already exist
  --no-summary                Use the non-summary dataset (Tom-Melb/CodeReviewQA)
  --csv-only                  Skip inference, only regenerate CSV summaries
  --dry-run                   Print commands without executing
  --results-dir DIR           Output directory (default: results)
```

## Results Structure

```
results/
├── acr/
│   └── acr_results.csv          # Per-language ACR exact-match scores
├── ctr/
│   └── ctr_results.csv          # Per-language CTR invariant accuracy
├── cl/
│   ├── cl_easy_results.csv      # Per-language CL easy invariant accuracy
│   └── cl_hard_results.csv      # Per-language CL hard invariant accuracy
├── si/
│   ├── si_easy_results.csv      # Per-language SI easy invariant accuracy
│   └── si_hard_results.csv      # Per-language SI hard invariant accuracy
└── global_rerults.csv           # Summary: one row per model (ACR/CTR/CLE/CLH/SIE/SIE)
```

## Scoring

- **ACR**: Exact-match rate (`em` column), reported as percentage per language
- **CTR / CL / SI**: Invariant accuracy (correct only if the model picks the right answer in *every* permutation), reported as percentage per language
- **Overall**: Pooled score across all languages (weighted by number of examples)

## File Structure

```
.
├── ACR_vLLM.py              # Inference for Automated Code Refinement
├── CL_vLLM.py               # Inference for Change Localisation
├── CTR_vLLM.py              # Inference for Change Type Recognition
├── SI_vLLM.py               # Inference for Solution Identification
├── main.py                  # Driver: runs all tasks, aggregates CSV results
├── utils.py                 # Prompt templates and evaluation functions
├── requirements.txt         # Python dependencies (vllm, pandas, tqdm)
├── slurm/
│   ├── run_1gpu.sh          # Slurm batch for ≤16B models
│   ├── run_2gpu.sh          # Slurm batch for ≤34B models
│   └── run_4gpu.sh          # Slurm batch for ≤72B models
├── results/                 # Inference outputs and CSV summaries
│   ├── acr/                 #   ACR pkl results and CSV
│   ├── ctr/                 #   CTR pkl results and CSV
│   ├── cl/                  #   CL pkl results and CSVs (easy/hard)
│   ├── si/                  #   SI pkl results and CSVs (easy/hard)
│   └── global_rerults.csv   #   Cross-task model summary
├── graphics/
├── LICENSE
└── README.md
```

## Reference

```bibtex
@inproceedings{,
    title = "Do AI-Generated PR Summaries Improve Code Review?",
    author = "Azer Ben Chakir,
    Raed Affes",
    booktitle = "",
    month = Aug,
    year = "2026",
    address = "Manouba, Tunisia",
    publisher = "Not published yet",
    url = "https://soon.org",
    doi = "",
    pages = "",
    ISBN = ""
}
```