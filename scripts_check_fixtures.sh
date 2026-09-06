#!/usr/bin/env bash
set -e
cd /home/azer/CodeReviewQA/prototype
../.venv/bin/python scripts/build_fixtures.py
../.venv/bin/python - <<'PY'
import os, sys, json
sys.path.insert(0, os.getcwd())
from pathlib import Path
from github_client import parse_unified_diff
from pr_decomposer.bug_review import parse_bug_review

# 1) every fixture diff must parse to files with content
for p in sorted(Path("fixtures").glob("*.json")):
    fx = json.loads(p.read_text())
    files = parse_unified_diff(fx["diff"])
    total = sum(f.additions for f in files)
    assert files, f"fixture {fx['name']}: no files parsed"
    assert total > 10, f"fixture {fx['name']}: too few additions ({total})"
    print(f"{fx['name']}: {len(files)} file(s), +{total}")

# 2) parse_bug_review on a hand-made block incl. multi-line verdict + inline sev
raw = """BUGS:
BUG 1: critical
TYPE: logic
TITLE: off-by-one
LOCATION: cart/pricing.py:9
DETAIL: Integer division truncates toward zero, dropping the cent.
DETAIL continuation line.
FIX: Use Decimal rounding.
BUG 2:
SEVERITY: minor
TYPE: edge-case
TITLE: retry re-applies discount
LOCATION: cart/api.py:14
DETAIL: Retried requests double-apply the discount.
REQUIREMENTS:
REQ 1: satisfied - prices exact to the cent
REQUIREMENT: prices exact to the cent
STATUS: satisfied
EVIDENCE: Decimal used.
REQ 2:
REQUIREMENT: idempotent discount
STATUS: unmet
EVIDENCE: cart/api.py applies the discount again on retry.
REQUIREMENTS_VERDICT: The cent-exactness requirement is met, but idempotency
is violated: a retried request re-applies the same discount, changing the
total. This is a real incompatibility for the reviewer to consider.
MERGE_READINESS: fix-before-merge
"""
r = parse_bug_review(raw)
assert len(r.findings) == 2, r.findings
assert r.findings[0].severity == "critical" and r.findings[0].bug_type == "logic"
assert "continuation" in r.findings[0].detail
assert r.findings[1].bug_type == "edge-case"
assert len(r.checks) == 2, r.checks
assert r.checks[0].status == "satisfied"
assert r.checks[1].status == "unmet"
assert "idempotency" in r.requirements_verdict and "reviewer" in r.requirements_verdict
assert r.merge_readiness == "fix-before-merge"
print("parse_bug_review: OK (inline severity, continuation lines, multi-line verdict)")

# 3) pragmatic: bug title keyword matching helper used by benchmark
from benchmark_models import _match_bug
class F:
    def __init__(self, title, location, btype):
        self.title, self.location, self.type = title, location, btype
exp = {"type": "logic", "severity": "critical", "path": "cart/pricing.py",
       "keywords": ["round", "trunc"]}
assert _match_bug(F("float truncation loses cents", "cart/pricing.py:9", "logic"), exp)
assert not _match_bug(F("unrelated", "cart/api.py:1", "logic"), exp)
print("benchmark matching: OK")
PY