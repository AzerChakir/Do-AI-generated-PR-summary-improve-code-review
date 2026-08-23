#!/usr/bin/env bash
set -euo pipefail

# Empty (truncate to 0 bytes) all .csv files recursively, without deleting them.
# Usage: ./emptycsv.sh          -> dry run (shows what would be emptied)
#        ./emptycsv.sh --run    -> actually truncate the files

if [[ "${1:-}" == "--run" ]]; then
    find . -name ".venv" -prune -o -type f -name "*.csv" -print -exec truncate -s 0 {} \;
    echo "Done. Emptied all .csv files under: $(pwd)"
else
    echo "DRY RUN - no files modified. Re-run with --run to empty these files:"
    find . -name ".venv" -prune -o -type f -name "*.csv" -print
fi
