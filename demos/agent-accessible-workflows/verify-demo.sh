#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$ROOT_DIR/src"
ENV_PATH="$SRC_DIR/.env"
CHECK_QUEUE="${CHECK_QUEUE:-false}"

if [[ ! -f "$ENV_PATH" ]]; then
  echo "Missing $ENV_PATH. Run ./start-demo.sh first." >&2
  exit 1
fi

token="$(rg '^API_TOKEN=' "$ENV_PATH" -n -N | sed 's/^API_TOKEN=//' || true)"
if [[ -z "${token:-}" ]]; then
  echo "Missing API_TOKEN in $ENV_PATH" >&2
  exit 1
fi

echo "Checking API health..."
health="$(curl -fsS "http://localhost:8000/healthz")"
echo "$health" | rg '"status"\s*:\s*"ok"' >/dev/null
echo "Health check passed."

echo "Submitting synthetic smoke run..."
resp="$(curl -fsS -X POST "http://localhost:8000/tools/run_deseq" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $token" \
  --data-binary "@$SRC_DIR/fixtures/run-deseq-synthetic.json")"
echo "$resp"
job_id="$(printf "%s" "$resp" | python3 - <<'PY'
import json,sys
try:
    data=json.load(sys.stdin)
except Exception:
    print("")
    raise
print(data.get("job_id",""))
PY
)"
if [[ -z "$job_id" ]]; then
  echo "No job_id found in smoke run response." >&2
  exit 1
fi
echo "Smoke run returned job_id=$job_id"

if [[ "$CHECK_QUEUE" == "true" ]]; then
  echo "Submitting 2 queue stress requests..."
  for i in 1 2; do
    curl -fsS -X POST "http://localhost:8000/tools/run_deseq" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $token" \
      --data-binary "@$SRC_DIR/fixtures/run-deseq-synthetic.json" | tee /tmp/deseq-queue-$i.json
    echo ""
  done
  echo "If ENABLE_RQ=true, responses should include status=queued."
fi

echo "Verification complete."
