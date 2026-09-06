#!/usr/bin/env bash
set -e
cd /home/azer/CodeReviewQA/prototype
../.venv/bin/python - <<'PY'
import sys, json, glob
sys.path.insert(0, "/home/azer/CodeReviewQA/prototype")
from pr_decomposer.report_export import build_html, build_pdf, build_markdown, md_to_html

rich = {
    "title": "PR #1337 — auth token rotation with retry cache ✓",
    "repo": "acme/identity", "pr_number": 1337,
    "stats": "+1,204 −86 in 14 files", "model": "nvidia/nemotron-3-super-120b-a12b",
    "effort": "medium", "analyzed_at_iso": "2026-09-05T18:28:03.123456+00:00",
    "verdict": "needs-work", "merge_readiness": "fix-before-merge",
    "summary": "Rotates JWTs every 12h. Adds in-memory retry cache.</think> ǝpoɔ → em-dash.",
    "concerns": [
        {"number": "1", "title": "Concurrency on token refresh", "change_type": "architecture",
         "rationale": "Two writers may both refresh; need locking.", "files": ["auth/rotate.py"],
         "is_mixed": True, "mixed_note": "Half caching, half rotation."},
    ],
    "change_log": [
        {"area": "auth/rotate.py", "files": ["auth/rotate.py"],
         "old_code": "def rotate():\n    return _raw()", "new_code": "def rotate():\n    with _lock: return _raw(refresh=True)",
         "impact": "Serialized under a lock."},
    ],
    "post_review": [
        {"number": 1, "severity": "minor", "title": "Dangling stdio handle",
         "files": ["main.go"], "body": "Log pipe never closed."},
    ],
    "post_review_verdict": "OK except handle leak.",
    "bug_findings": [
        {"number": 1, "severity": "important", "type": "logic", "title": "Cache never invalidated",
         "location": "auth/cache.py:41", "detail": "Entries live forever.",
         "fix": "Add TTL eviction."},
    ],
    "requirements_checks": [
        {"number": 1, "requirement": "Must not log tokens", "status": "satisfied", "evidence": "No logger sees the raw JWT."},
        {"number": 2, "requirement": "Rotation enforced", "status": "unmet", "evidence": "Not found."},
    ],
    "requirements_verdict": "Reject until enforcement lands.",
    "flags": [{"severity": "warning", "category": "merge-conflict", "message": "rotates shared file", "files": ["auth/rotate.py"]}],
    "plan_markdown": "# Decomposition\n\n1. **PR A**\n2. **PR B**\n\n```\ncode\n```\n",
}

decks = [rich] + [json.load(open(p, encoding="utf-8")) for p in glob.glob("data/reports/*.json")]
for i, deck in enumerate(decks):
    h = build_html(deck)
    m = build_markdown(deck)
    pdf = build_pdf(deck)
    assert h.startswith("<!doctype html>") and pdf.startswith(b"%PDF") and m.startswith("# "), i
    assert "\x00" not in m, f"nul in md {i}"
    print(f"report {i}: html={len(h)} md={len(m)} pdf={len(pdf)}")

md = build_markdown(rich)
for needle in ("# PR #", "**Verdict:**", "**Merge readiness", "## Concerns", "## Bugs",
               "## Requirements", "## Flags", "## Suggested decomposition",
               "**Suggested fix:**", "```text"):
    assert needle in md, f"missing {needle!r} in md"
print("md rich checks ok")

print("STRESS_OK")
PY