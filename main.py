"""
main.py
=======
Driver script for the CodeReviewQA repo. Runs ACR_vLLM.py / CTR_vLLM.py /
CL_vLLM.py / SI_vLLM.py for every task x language (and, for CL/SI, every
difficulty mode) for each model in MODEL_LIST, then aggregates the resulting
.pkl files into CSV tables saved inside the results/ directory:

  * Per-task CSVs (rows = model, columns = the 9 languages + an Overall
    column), written into each task's own directory:
      results/acr/acr_results.csv
      results/ctr/ctr_results.csv
      results/cl/cl_easy_results.csv   results/cl/cl_hard_results.csv
      results/si/si_easy_results.csv   results/si/si_hard_results.csv
  * results/global_rerults.csv - one row per model summarising the Overall
    of every task (ACR / CTR / CLE / CLH / SIE / SIH).

CSV rows are merged per model and never lose existing data: a model that is
not present yet gets a new line appended; for a model that already has a line
only the language cells for which fresh pkl results exist are written, while
the saved overall (and the global summary cells) are left untouched. No saved
value is ever erased or blanked. To fully refresh an existing model's row,
delete its CSV lines first.

Scoring mirrors utils.py exactly:
  * ACR: exact-match on the `em` column, 100 * mean(em) per language.
  * CTR / CL / SI: invariant accuracy, 100 * mean(row.model_answers ==
    row.correct_answers) per language.
  * Overall per task = pooled score across the languages present for that
    model (100 * total_correct / total_examples).

Place this file in the root of the CodeReviewQA repo (next to ACR_vLLM.py,
CTR_vLLM.py, CL_vLLM.py, SI_vLLM.py, and utils.py).

--------------------------------------------------------------------------
 EDIT THESE CONSTANTS BEFORE RUNNING
--------------------------------------------------------------------------
"""

MODEL_LIST = [
    # ── ≤3B models (1 GPU, --gpus=h100:1) ──────────────────────────
    "meta-llama/Llama-3.2-1B-Instruct",
    "meta-llama/Llama-3.2-3B-Instruct",
    "Qwen/Qwen2.5-1.5B-Instruct",
    "Qwen/Qwen2.5-3B-Instruct",
    "Qwen/Qwen2.5-Coder-1.5B-Instruct",
    "Qwen/Qwen2.5-Coder-3B-Instruct",
    "deepseek-ai/deepseek-coder-1.3b-instruct",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
    "tiiuae/Falcon3-1B-Instruct",
    "tiiuae/Falcon3-3B-Instruct",
    "microsoft/Phi-3-mini-128k-instruct",
    "01-ai/Yi-Coder-1.5B-Chat",
    "ibm-granite/granite-3b-code-instruct-128k",
    "ibm-granite/granite-3.0-3b-a800m-instruct",
    "ibm-granite/granite-3.0-2b-instruct",
    "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct",
    "internlm/internlm2_5-1_8b-chat",
    "stabilityai/stable-code-instruct-3b",

    # ── ≤9B models (1 GPU, --gpus=h100:1) ──────────────────────────
    "meta-llama/CodeLlama-7b-Instruct-hf",
    "meta-llama/Llama-3.1-8B-Instruct",
    "google/codegemma-1.1-7b-it",
    "google/gemma-2-9b-it",
    "Qwen/Qwen2.5-7B-Instruct",
    "Qwen/Qwen2.5-Coder-7B-Instruct",
    "AIDC-AI/Marco-o1",
    "deepseek-ai/deepseek-coder-7b-instruct-v1.5",
    "deepseek-ai/deepseek-llm-7b-chat",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
    "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
    "tiiuae/Falcon3-7B-Instruct",
    "baichuan-inc/Baichuan2-7B-Chat",
    "01-ai/Yi-Coder-9B-Chat",
    "01-ai/Yi-1.5-9B-Chat",
    "ibm-granite/granite-8b-code-instruct-128k",
    "ibm-granite/granite-3.0-8b-instruct",
    "LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct",

    # ── ≤16B models (1 GPU, --gpus=h100:1) ─────────────────────────
    "meta-llama/CodeLlama-13b-Instruct-hf",
    "Qwen/Qwen2.5-14B-Instruct",
    "Qwen/Qwen2.5-Coder-14B-Instruct",
    "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
    "deepseek-ai/DeepSeek-V2-Lite-Chat",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",
    "tiiuae/falcon-11B",
    "tiiuae/Falcon3-10B-Instruct",
    "baichuan-inc/Baichuan2-13B-Chat",
    "WizardLMTeam/WizardLM-13B-V1.2",
    "microsoft/Phi-3-medium-128k-instruct",
    "microsoft/phi-4",
    "bigcode/starcoder2-15b-instruct-v0.1",
    "mistralai/Mistral-Nemo-Instruct-2407",

    # ── ≤34B models (2 GPUs, --gpus=h100:2) ────────────────────────
    "meta-llama/CodeLlama-34b-Instruct-hf",
    "google/gemma-2-27b-it",
    "Qwen/Qwen2.5-32B-Instruct",
    "Qwen/Qwen2.5-Coder-32B-Instruct",
    "Qwen/QwQ-32B",
    "NovaSky-AI/Sky-T1-32B-Preview",
    "deepseek-ai/deepseek-coder-33b-instruct",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
    "01-ai/Yi-1.5-34B-Chat",
    "mistralai/Mistral-Small-Instruct-2409",
    "ibm-granite/granite-34b-code-instruct-8k",
    "internlm/internlm2_5-20b-chat",
    "LGAI-EXAONE/EXAONE-3.5-32B-Instruct",

    # ── ≤72B models (4 GPUs, --gpus=h100:4) ────────────────────────
    "meta-llama/CodeLlama-70b-Instruct-hf",
    "meta-llama/Llama-3.1-70B-Instruct",
    "meta-llama/Llama-3.3-70B-Instruct",
    "Qwen/Qwen2.5-72B-Instruct",
    "deepseek-ai/deepseek-llm-67b-chat",
    "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
    "WizardLMTeam/WizardLM-70B-V1.0",
    "LLM360/K2-Chat",
    "tiiuae/falcon-40b-instruct",
]

HF_TOKEN = "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"  # Your HF access token

# --------------------------------------------------------------------------
# WARNING: do not commit a real token to version control. If this file is
# tracked by git, either add it to .gitignore or move the constant above
# into an untracked local file / environment variable and read it from
# there instead.
# --------------------------------------------------------------------------

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent
RESULTS_DIR = REPO_ROOT / "results"

# Exactly the language argument strings the four *_vLLM.py scripts expect
# (see README "Usage"): language.lower() must match the dataset's `lang`
# column / the results/<task>/<lang> folder names (c, cpp, csharp, go,
# java, javascript, php, python, ruby).
LANGUAGES = ["C", "CPP", "CSharp", "Go", "Java", "JavaScript", "PHP", "Python", "Ruby"]
MODES = ["easy", "hard"]  # only used for CL / SI
LANGS = ["c", "cpp", "csharp", "go", "java", "javascript", "php", "python", "ruby"]

SCRIPTS = {
    "ACR": REPO_ROOT / "ACR_vLLM.py",
    "CTR": REPO_ROOT / "CTR_vLLM.py",
    "CL": REPO_ROOT / "CL_vLLM.py",
    "SI": REPO_ROOT / "SI_vLLM.py",
}

# Task label -> (results sub-dir, csv filename). The CSV column layout
# matches the placeholders shipped in the repo
# (model,c,cpp,csharp,go,java,javascript,php,python,ruby,overall).
TASK_CSV_FILES = {
    "ACR": ("acr", "acr_results.csv"),
    "CTR": ("ctr", "ctr_results.csv"),
    "CL_Easy": ("cl", "cl_easy_results.csv"),
    "CL_Hard": ("cl", "cl_hard_results.csv"),
    "SI_Easy": ("si", "si_easy_results.csv"),
    "SI_Hard": ("si", "si_hard_results.csv"),
}

ACR_METRIC = "em"  # one of em / em_trim / em_no_space / em_no_comment


def model_name_short(model_name: str) -> str:
    """Matches `model_name.split("/")[1]` used inside every *_vLLM.py script."""
    parts = model_name.split("/")
    if len(parts) < 2:
        raise ValueError(
            f"MODEL_NAME '{model_name}' must be in 'org/model' form, "
            "matching what the *_vLLM.py scripts expect."
        )
    return parts[1]


def expected_output_path(task: str, lang: str, model_short: str, mode: str | None = None, results_dir: Path = RESULTS_DIR) -> Path:
    """Reproduces each script's own `save_dir` naming exactly (under the
    given results_dir), so we can tell whether a given (task, language[,
    mode]) run has already been done for this model."""
    lang_l = lang.lower()
    if task == "ACR":
        return results_dir / "acr" / lang_l / f"acr_{lang_l}_{model_short}.pkl"
    if task == "CTR":
        return results_dir / "ctr" / lang_l / f"ctr_{lang_l}_{model_short}.pkl"
    if task in ("CL", "SI"):
        assert mode in MODES
        t = task.lower()
        return results_dir / t / lang_l / mode / f"{t}_{mode}_{lang_l}_{model_short}.pkl"
    raise ValueError(f"Unknown task '{task}'")


def ensure_result_dirs(results_dir: Path):
    """Create the <results_dir>/<task>/<lang>[/<mode>] tree if it isn't
    already there (the repo ships with it pre-created, but this makes the
    script self-sufficient on a fresh checkout too)."""
    for lang in LANGUAGES:
        lang_l = lang.lower()
        (results_dir / "acr" / lang_l).mkdir(parents=True, exist_ok=True)
        (results_dir / "ctr" / lang_l).mkdir(parents=True, exist_ok=True)
        for task in ("cl", "si"):
            for mode in MODES:
                (results_dir / task / lang_l / mode).mkdir(parents=True, exist_ok=True)


def build_commands(model_name: str, hf_token: str, model_short: str, skip_existing: bool, with_summary: bool, results_dir: Path = RESULTS_DIR):
    """Yields (task, lang, mode_or_None, command_list, output_path) for
    every run that needs to happen, in the same argument order the
    README documents for each script."""
    for lang in LANGUAGES:
        # ACR
        out = expected_output_path("ACR", lang, model_short, results_dir=results_dir)
        if not (skip_existing and out.exists()):
            yield ("ACR", lang, None, [sys.executable, str(SCRIPTS["ACR"]), hf_token, lang, model_name] , out)

        # CTR
        out = expected_output_path("CTR", lang, model_short, results_dir=results_dir)
        if not (skip_existing and out.exists()):
            yield ("CTR", lang, None, [sys.executable, str(SCRIPTS["CTR"]), hf_token, lang, model_name] , out)

        # CL, easy + hard
        for mode in MODES:
            out = expected_output_path("CL", lang, model_short, mode, results_dir=results_dir)
            if not (skip_existing and out.exists()):
                yield ("CL", lang, mode, [sys.executable, str(SCRIPTS["CL"]), hf_token, lang, mode, model_name], out)

        # SI, easy + hard
        for mode in MODES:
            out = expected_output_path("SI", lang, model_short, mode, results_dir=results_dir)
            if not (skip_existing and out.exists()):
                yield ("SI", lang, mode, [sys.executable, str(SCRIPTS["SI"]), hf_token, lang, mode, model_name] , out)


def run_all(model_list: list, hf_token: str, skip_existing: bool, dry_run: bool, results_dir: Path = RESULTS_DIR, with_summary: bool = True):
    ensure_result_dirs(results_dir)
    all_failures = []

    for model_name in model_list:
        model_short = model_name_short(model_name)
        commands = list(build_commands(model_name, hf_token, model_short, skip_existing, with_summary, results_dir))
        total = len(commands)
        print(f"\n{'='*60}")
        print(f"Model: {model_name}  ({total} run(s) queued out of {9 * 6} possible)")
        print(f"{'='*60}")

        if total == 0:
            print("Nothing to do — all outputs already exist for this model. "
                  "Pass --no-skip-existing to force a re-run.")
            continue

        for i, (task, lang, mode, cmd, out_path) in enumerate(commands, start=1):
            label = f"{task} / {lang}" + (f" / {mode}" if mode else "")
            print(f"\n[{i}/{total}] {label}")
            print("  $ " + " ".join(c if c != hf_token else "***" for c in cmd))

            if dry_run:
                continue

            start = time.time()
            env = dict(os.environ, CRQA_RESULTS_DIR=str(results_dir))
            result = subprocess.run(cmd, cwd=REPO_ROOT, env=env)
            elapsed = time.time() - start

            if result.returncode != 0:
                print(f"  FAILED ({label}) after {elapsed:.0f}s, return code {result.returncode}")
                all_failures.append(f"{model_name}: {label}")
            elif not out_path.exists():
                print(f"  WARNING: script exited 0 but expected output not found at {out_path}")
                all_failures.append(f"{model_name}: {label}")
            else:
                print(f"  done in {elapsed:.0f}s -> {out_path}")

    if dry_run:
        print("\nDry run complete — no scripts were actually executed.")
        return all_failures

    print(f"\nFinished {len(model_list)} model(s). Total failures: {len(all_failures)}")
    if all_failures:
        print("The following runs failed or produced no output:")
        for f in all_failures:
            print(f"  - {f}")
    return all_failures


# --------------------------------------------------------------------------
# CSV aggregation (reads the .pkl files, mirrors the scoring in utils.py)
# --------------------------------------------------------------------------

def _model_from_filename(filename: str, prefix: str) -> str:
    """Recover the model_name_short the *_vLLM.py scripts embed in the pkl
    filename by stripping the known task/lang[/mode] prefix + .pkl suffix."""
    stem = filename[:-4] if filename.endswith(".pkl") else filename
    if not stem.startswith(prefix):
        raise ValueError(f"Unexpected result filename '{filename}' for prefix '{prefix}'")
    return stem[len(prefix):]


def _score_acr_file(path: Path) -> tuple:
    df = pd.read_pickle(path)
    n = len(df)
    if n == 0:
        return float("nan"), 0
    return 100.0 * df[ACR_METRIC].sum() / n, n


def _score_mcqa_file(path: Path) -> tuple:
    """Invariant accuracy: correct only if the model picked the correct
    option symbol in *every* permutation (utils.calc_results)."""
    df = pd.read_pickle(path)
    n = len(df)
    if n == 0:
        return float("nan"), 0
    correct = (df["model_answers"] == df["correct_answers"]).sum()
    return 100.0 * correct / n, n


def _collect_scores(results_dir: Path) -> dict:
    """Return {task label: {model: {lang: (score, n)}}} for every task."""
    out = {}

    acr = {}
    for lang in LANGS:
        for f in (results_dir / "acr" / lang).glob("acr_*.pkl"):
            model = _model_from_filename(f.name, f"acr_{lang}_")
            acr.setdefault(model, {})[lang] = _score_acr_file(f)
    out["ACR"] = acr

    ctr = {}
    for lang in LANGS:
        for f in (results_dir / "ctr" / lang).glob("ctr_*.pkl"):
            model = _model_from_filename(f.name, f"ctr_{lang}_")
            ctr.setdefault(model, {})[lang] = _score_mcqa_file(f)
    out["CTR"] = ctr

    for task in ("cl", "si"):
        for mode in MODES:
            label = f"{task.upper()}_{mode.capitalize()}"
            bucket = {}
            for lang in LANGS:
                for f in (results_dir / task / lang / mode).glob(f"{task}_{mode}_{lang}_*.pkl"):
                    model = _model_from_filename(f.name, f"{task}_{mode}_{lang}_")
                    bucket.setdefault(model, {})[lang] = _score_mcqa_file(f)
            out[label] = bucket

    return out


def _wide_rows(per_model_langs: dict) -> list:
    """Build the per-task CSV rows: model + 9 language scores + pooled Overall
    (blank for languages the model was not run on)."""
    rows = []
    for model in sorted(per_model_langs):
        row = {"model": model}
        total_correct = 0.0
        total_n = 0
        for lang in LANGS:
            if lang in per_model_langs[model]:
                score, n = per_model_langs[model][lang]
                row[lang] = score
                total_correct += score / 100.0 * n
                total_n += n
            else:
                row[lang] = ""
        row["overall"] = (100.0 * total_correct / total_n) if total_n else ""
        rows.append(row)
    return rows


def _is_blank(value) -> bool:
    return value is None or value == "" or (isinstance(value, float) and pd.isna(value))


def _merge_rows(existing_rows: list, new_rows: list) -> list:
    """Merge fresh rows over existing ones (keyed by model) without ever
    erasing a saved value.

    * a model with no existing line gets its fresh row appended as-is;
    * a model that already has a line only receives the language cells for
      which the fresh row carries a non-blank score, while its saved overall
      (and any cell without fresh data) is left untouched.
    Sorted by model name."""
    merged = {row["model"]: dict(row) for row in existing_rows}
    for row in new_rows:
        model = row["model"]
        if model not in merged:
            merged[model] = dict(row)
            continue
        current = merged[model]
        for lang in LANGS:
            if not _is_blank(row[lang]):
                current[lang] = row[lang]
    return [merged[m] for m in sorted(merged)]


def _read_existing_rows(csv_path: Path, model_col: str) -> list:
    if not csv_path.exists():
        return []
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return []
    if model_col not in df.columns:
        return []
    return df.to_dict("records")


def generate_csvs(results_dir: Path = None):
    """Aggregate every model's pkl results into the per-task CSVs (placed in
    each task's own directory) and into results/global_rerults.csv. Rows are
    merged per model name: new models are appended, and for existing models
    only cells backed by fresh pkl data are written — no saved value is ever
    erased or blanked."""
    results_dir = Path(results_dir) if results_dir else RESULTS_DIR

    task_tables = _collect_scores(results_dir)
    summary_cols = ["ACR", "CTR", "CLE", "CLH", "SIE", "SIH"]
    summary_labels = ["ACR", "CTR", "CL_Easy", "CL_Hard", "SI_Easy", "SI_Hard"]

    for label, (subdir, fname) in TASK_CSV_FILES.items():
        csv_path = results_dir / subdir / fname
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        columns = ["model"] + LANGS + ["overall"]
        rows = _merge_rows(_read_existing_rows(csv_path, "model"), _wide_rows(task_tables[label]))
        pd.DataFrame(rows, columns=columns).to_csv(csv_path, index=False)
        print(f"[CSV] {label}: {csv_path} ({len(rows)} model(s))")

    summary_path = results_dir / "global_rerults.csv"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_by_model = {r["model"]: dict(r) for r in _read_existing_rows(summary_path, "model")}
    for col_name, label in zip(summary_cols, summary_labels):
        for model, per_model_langs in task_tables[label].items():
            total_correct = sum(score / 100.0 * n for score, n in per_model_langs.values())
            total_n = sum(n for _, n in per_model_langs.values())
            value = 100.0 * total_correct / total_n if total_n else ""
            current = summary_by_model.setdefault(model, {"model": model})
            if _is_blank(current.get(col_name)):
                current[col_name] = value
    summary_rows = [summary_by_model[m] for m in sorted(summary_by_model)]
    pd.DataFrame(summary_rows, columns=["model"] + summary_cols).to_csv(summary_path, index=False)
    print(f"[CSV] GLOBAL: {summary_path} ({len(summary_rows)} model(s))")


def main():
    parser = argparse.ArgumentParser(
        description="Run all CodeReviewQA tasks across all languages for each "
                     "model in MODEL_LIST, then aggregate the results into "
                     "per-task CSVs and results/global_rerults.csv."
    )
    parser.add_argument(
        "--no-skip-existing", dest="skip_existing", action="store_false",
        help="Re-run every task/language/mode even if its output .pkl already exists "
             "for this model (default: skip ones that already exist).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print the commands that would be run without actually executing "
             "anything or writing any CSV.",
    )
    parser.add_argument(
        "--csv-only", action="store_true",
        help="Skip running the inference scripts entirely and only (re)generate "
             "the CSV summaries from whatever results already exist.",
    )
    parser.add_argument(
        "--results-dir", type=str, default="results",
        help="Output directory (relative to the repo root) where experiment "
             ".pkl results and generated CSVs live. Use a separate value to keep "
             "an experiment isolated from previous ones, e.g. "
             "--results-dir results/summary for the summary-dataset runs so the "
             "old results/ CSVs (non-summary dataset) are left untouched.",
    )
    parser.add_argument(
        "--no-summary", dest="with_summary", action="store_false",
        help="Do NOT pass --summary to the *_vLLM.py scripts, i.e. use the "
             "non-summary dataset Tomo-Melb/CodeReviewQA instead of "
             "AzerChakir/CodeReviewWithSummaryQA (default: summary is ON).",
    )
    parser.add_argument(
        "--tier", type=str, choices=["small", "medium", "large"],
        help="Run only models from a specific GPU tier instead of all of MODEL_LIST. "
             "small=≤16B (1 GPU), medium=≤34B (2 GPUs), large=≤72B (4 GPUs).",
    )
    parser.set_defaults(with_summary=True)
    args = parser.parse_args()

    model_list = MODEL_LIST
    if args.tier:
        MODEL_TIERS = {
            "small": [
                "meta-llama/Llama-3.2-1B-Instruct",
                "meta-llama/Llama-3.2-3B-Instruct",
                "Qwen/Qwen2.5-1.5B-Instruct",
                "Qwen/Qwen2.5-3B-Instruct",
                "Qwen/Qwen2.5-Coder-1.5B-Instruct",
                "Qwen/Qwen2.5-Coder-3B-Instruct",
                "deepseek-ai/deepseek-coder-1.3b-instruct",
                "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
                "tiiuae/Falcon3-1B-Instruct",
                "tiiuae/Falcon3-3B-Instruct",
                "microsoft/Phi-3-mini-128k-instruct",
                "01-ai/Yi-Coder-1.5B-Chat",
                "ibm-granite/granite-3b-code-instruct-128k",
                "ibm-granite/granite-3.0-3b-a800m-instruct",
                "ibm-granite/granite-3.0-2b-instruct",
                "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct",
                "internlm/internlm2_5-1_8b-chat",
                "stabilityai/stable-code-instruct-3b",
                "meta-llama/CodeLlama-7b-Instruct-hf",
                "meta-llama/Llama-3.1-8B-Instruct",
                "google/codegemma-1.1-7b-it",
                "google/gemma-2-9b-it",
                "Qwen/Qwen2.5-7B-Instruct",
                "Qwen/Qwen2.5-Coder-7B-Instruct",
                "AIDC-AI/Marco-o1",
                "deepseek-ai/deepseek-coder-7b-instruct-v1.5",
                "deepseek-ai/deepseek-llm-7b-chat",
                "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
                "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
                "tiiuae/Falcon3-7B-Instruct",
                "baichuan-inc/Baichuan2-7B-Chat",
                "01-ai/Yi-Coder-9B-Chat",
                "01-ai/Yi-1.5-9B-Chat",
                "ibm-granite/granite-8b-code-instruct-128k",
                "ibm-granite/granite-3.0-8b-instruct",
                "LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct",
                "meta-llama/CodeLlama-13b-Instruct-hf",
                "Qwen/Qwen2.5-14B-Instruct",
                "Qwen/Qwen2.5-Coder-14B-Instruct",
                "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
                "deepseek-ai/DeepSeek-V2-Lite-Chat",
                "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",
                "tiiuae/falcon-11B",
                "tiiuae/Falcon3-10B-Instruct",
                "baichuan-inc/Baichuan2-13B-Chat",
                "WizardLMTeam/WizardLM-13B-V1.2",
                "microsoft/Phi-3-medium-128k-instruct",
                "microsoft/phi-4",
                "bigcode/starcoder2-15b-instruct-v0.1",
                "mistralai/Mistral-Nemo-Instruct-2407",
            ],
            "medium": [
                "meta-llama/CodeLlama-34b-Instruct-hf",
                "google/gemma-2-27b-it",
                "Qwen/Qwen2.5-32B-Instruct",
                "Qwen/Qwen2.5-Coder-32B-Instruct",
                "Qwen/QwQ-32B",
                "NovaSky-AI/Sky-T1-32B-Preview",
                "deepseek-ai/deepseek-coder-33b-instruct",
                "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
                "01-ai/Yi-1.5-34B-Chat",
                "mistralai/Mistral-Small-Instruct-2409",
                "ibm-granite/granite-34b-code-instruct-8k",
                "internlm/internlm2_5-20b-chat",
                "LGAI-EXAONE/EXAONE-3.5-32B-Instruct",
            ],
            "large": [
                "meta-llama/CodeLlama-70b-Instruct-hf",
                "meta-llama/Llama-3.1-70B-Instruct",
                "meta-llama/Llama-3.3-70B-Instruct",
                "Qwen/Qwen2.5-72B-Instruct",
                "deepseek-ai/deepseek-llm-67b-chat",
                "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
                "WizardLMTeam/WizardLM-70B-V1.0",
                "LLM360/K2-Chat",
                "tiiuae/falcon-40b-instruct",
            ],
        }
        model_list = MODEL_TIERS[args.tier]
        print(f"Tier '{args.tier}': {len(model_list)} model(s)")

    if not model_list:
        print("ERROR: No models to run. Edit MODEL_LIST in main.py or use --tier.")
        sys.exit(1)

    results_dir = Path(args.results_dir)
    if not results_dir.is_absolute():
        results_dir = REPO_ROOT / results_dir

    failures = []
    if not args.csv_only:
        failures = run_all(model_list, HF_TOKEN, args.skip_existing, args.dry_run, results_dir, args.with_summary)

    if args.dry_run:
        print("Dry run complete — CSV export was not actually executed.")
    else:
        print("\n--- Aggregating results into CSVs ---")
        generate_csvs(results_dir)

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
