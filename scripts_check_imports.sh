#!/usr/bin/env bash
set -e
cd /home/azer/CodeReviewQA/prototype
../.venv/bin/python -c "import pr_decomposer.bug_review, pr_decomposer.repo_context, pr_decomposer.models, api, cli, seed_report; print('imports ok')"