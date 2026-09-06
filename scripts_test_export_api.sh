#!/usr/bin/env bash
set -euo pipefail
cd /home/azer/CodeReviewQA/prototype
PORT=8001
RID=$(ls data/reports/*.json | grep -v mini | grep -v meta | head -1 | xargs -n1 basename | sed 's/.json$//')
echo "report_id: $RID"

../.venv/bin/python -m uvicorn api:app --port "$PORT" --log-level warning > /tmp/export_api.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT
sleep 5

echo "== health"
curl -s -m 5 "http://127.0.0.1:$PORT/api/health" | head -c 120; echo

echo "== export html (headers)"
curl -s -m 10 -D - "http://127.0.0.1:$PORT/api/reports/$RID/export?format=html" -o /tmp/export_test.html | head -6
echo "  html bytes: $(wc -c < /tmp/export_test.html)"
head -c 120 /tmp/export_test.html; echo; echo

echo "== export md (headers)"
curl -s -m 10 -D - "http://127.0.0.1:$PORT/api/reports/$RID/export?format=md" -o /tmp/export_test.md | head -6
echo "  md bytes: $(wc -c < /tmp/export_test.md)"
head -5 /tmp/export_test.md

echo "== md via markdown alias"
curl -s -m 10 -o /tmp/export_test2.md -w "%{http_code} %{content_type}\n" "http://127.0.0.1:$PORT/api/reports/$RID/export?format=markdown"
diff -q /tmp/export_test.md /tmp/export_test2.md && echo "  alias output identical"

echo "== export pdf (headers)"
curl -s -m 10 -D - "http://127.0.0.1:$PORT/api/reports/$RID/export?format=pdf" -o /tmp/export_test.pdf | head -6
file /tmp/export_test.pdf
head -c 8 /tmp/export_test.pdf | od -c | head -1

echo "== bad format"
curl -s -m 5 -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:$PORT/api/reports/$RID/export?format=xlsx"

echo "== unknown report"
curl -s -m 5 -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:$PORT/api/reports/nope-123/export?format=pdf"

echo "== default format (no param) -> html"
curl -s -m 5 -o /dev/null -w "%{http_code} %{content_type}\n" "http://127.0.0.1:$PORT/api/reports/$RID/export"

kill $SERVER 2>/dev/null || true
wait $SERVER 2>/dev/null || true
echo "DONE"