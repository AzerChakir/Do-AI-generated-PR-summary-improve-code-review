#!/usr/bin/env bash
set -euo pipefail

# Delete all .pkl files recursively from the current directory.
find . -type f -name "*.pkl" -print -delete

echo "Done. Removed all .pkl files under: $(pwd)"
