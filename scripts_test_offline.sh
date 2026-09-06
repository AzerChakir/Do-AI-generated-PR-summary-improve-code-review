#!/usr/bin/env bash
set -e
cd /home/azer/CodeReviewQA/prototype
../.venv/bin/python -m unittest tests.test_pipeline -v 2>&1