#!/usr/bin/env bash
set -e
cd /home/azer/CodeReviewQA/prototype
../.venv/bin/python - <<'PY'
import os, sys
sys.path.insert(0, os.getcwd())
from pathlib import Path
from github_client import LocalDiffSource
from pr_decomposer import run_pipeline, BugFinding, RequirementCheck
from pr_decomposer.config import load_config

diff = LocalDiffSource(os.path.join(ROOT := os.getcwd(), "example", "mixed_concern.diff")).fetch()
cfg = load_config(Path(ROOT) / ".env")
report = run_pipeline(diff, config=cfg, mock=True, effort="deep", requirements="REQ: avatars persist server-side")

print("summary:", repr(report.pr_summary))
print("concerns:", len(report.concerns), "flags:", len(report.flags), "change_log:", len(report.change_log))
print("post_review:", len(report.post_review), report.post_review_verdict[:60])
print("bug_findings:", len(report.bug_findings))
for b in report.bug_findings:
    print(" -", b.severity, b.bug_type, b.title, "|", b.location, "| fix:", (b.fix or "")[:50])
print("requirements_checks:", len(report.requirements_checks))
for c in report.requirements_checks:
    print(" -", c.status, ":", c.requirement[:60])
print("requirements_verdict:", (report.requirements_verdict or "")[:80])
print("merge_readiness:", report.merge_readiness, "| effort:", report.effort, "| model:", report.model)

keys = report.to_dict().keys()
print("dict has bug_findings:", "bug_findings" in keys, "| merge_readiness:", "merge_readiness" in keys)
assert "Bugs & risks" in report.plan_markdown
assert "Decision for the reviewer" in report.plan_markdown
assert report.merge_readiness == "fix-before-merge"
print("OK: mock pipeline with bug_review runs end to end")
PY