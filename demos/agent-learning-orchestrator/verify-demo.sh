#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$ROOT_DIR/src"
ENV_PATH="$SRC_DIR/.env"
ORCH_PORT="${ORCHESTRATOR_PORT:-8003}"
BASE="http://127.0.0.1:${ORCH_PORT}"

if [[ -f "$ENV_PATH" ]]; then
  token="$(python3 - "$ENV_PATH" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
for line in path.read_text(encoding="utf-8").splitlines():
    if line.strip().startswith("API_TOKEN="):
        print(line.split("=", 1)[1].strip())
        break
PY
)"
else
  token=""
fi

auth=()
if [[ -n "${token:-}" ]]; then
  auth=(-H "Authorization: Bearer $token")
fi

echo "Checking orchestrator health at $BASE ..."
health="$(curl -fsS "${auth[@]}" "$BASE/healthz")"
HEALTH="$health" python3 - <<'PY'
import json
import os

if json.loads(os.environ["HEALTH"]).get("status") != "ok":
    raise SystemExit("Health check did not return status=ok")
PY
echo "Health check passed."

echo "Starting trust-and-DE component (max 2 internal cycles)..."
resp="$(curl -fsS -X POST "${auth[@]}" "$BASE/tools/start_component" \
  -H "Content-Type: application/json" \
  -d '{"max_internal_cycles": 2}')"
echo "$resp"

action="$(RESP="$resp" python3 - <<'PY'
import json
import os
data = json.loads(os.environ["RESP"])
summary = data.get("component_summary") or {}
handoff = summary.get("parent_handoff") or {}
print(handoff.get("recommended_action", ""))
PY
)"
if [[ -z "$action" ]]; then
  echo "Missing parent_handoff.recommended_action in response." >&2
  exit 1
fi
echo "Handoff recommended_action=$action"

study_id="$(RESP="$resp" python3 - <<'PY'
import json
import os
data = json.loads(os.environ["RESP"])
summary = data.get("component_summary") or {}
study = summary.get("study") or {}
print(study.get("study_id", ""))
PY
)"
if [[ -z "$study_id" ]]; then
  echo "Missing component_summary.study.study_id in response." >&2
  exit 1
fi
echo "Shared study_id=$study_id"

run_id="$(RESP="$resp" python3 - <<'PY'
import json
import os
print(json.loads(os.environ["RESP"]).get("component_run_id", ""))
PY
)"
if [[ -n "$run_id" ]]; then
  echo "Fetching summary for $run_id ..."
  curl -fsS "${auth[@]}" "$BASE/components/$run_id/summary" | python3 -m json.tool | head -n 20
fi

echo "Verification complete."
