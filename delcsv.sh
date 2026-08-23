#!/usr/bin/env bash
set -euo pipefail

# Delete all .csv files recursively from the current directory.
# Skips .venv/ so installed package data is never touched.
# Usage: ./delcsv.sh          -> dry run (lists what would be deleted)
#        ./delcsv.sh --run    -> actually delete the files

if [[ "${1:-}" == "--run" ]]; then
    find . -name ".venv" -prune -o -type f -name "*.csv" -print -delete
    echo "Done. Deleted all .csv files under: $(pwd)"
else
    echo "DRY RUN - no files deleted. Re-run with --run to delete these files:"
    find . -name ".venv" -prune -o -type f -name "*.csv" -print
fi
