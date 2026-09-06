#!/usr/bin/env bash
set -e
cd /home/azer/CodeReviewQA/prototype
../.venv/bin/python - <<'PY'
import os, sys
sys.path.insert(0, os.getcwd())
from pathlib import Path
from github_client import LocalDiffSource
from pr_decomposer import run_pipeline
from pr_decomposer.config import load_config

diff = LocalDiffSource(os.path.join(os.getcwd(), "example", "mixed_concern.diff")).fetch()
cfg = load_config(Path(os.getcwd()) / ".env")
report = run_pipeline(diff, config=cfg, mock=True)

assert "Decision for the reviewer" in report.plan_markdown
assert "Merge readiness (advisory)" in report.plan_markdown
assert "Requirement compatibility" in report.plan_markdown
assert "Requirements verdict" in report.plan_markdown
print(report.plan_markdown[report.plan_markdown.index("## Decision"):])
PY