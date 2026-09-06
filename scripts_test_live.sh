#!/usr/bin/env bash
set -e
cd /home/azer/CodeReviewQA/prototype
export NIM_API_KEY=$(grep -E '^NIM_API_KEY=' .env | head -1 | cut -d= -f2)
export GITHUB_TOKEN=$(grep -E '^GITHUB_TOKEN=' .env | head -1 | cut -d= -f2)
../.venv/bin/python -u -m unittest tests.test_live -v 2>&1