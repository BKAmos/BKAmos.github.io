#!/usr/bin/env bash
set -euo pipefail

# Start the full local RNA-seq trust-and-DE learning loop with host uvicorn
# processes so all services can see the same demos/_shared_studies paths.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMOS_DIR="$(cd "$ROOT_DIR/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="${PYTHON:-python3}"

if [[ "${INSTALL_DEPS:-false}" == "true" || ! -x "$VENV_DIR/bin/python" ]]; then
  echo "Creating shared learning-loop virtual environment..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  "$VENV_DIR/bin/python" -m pip install --upgrade pip
  "$VENV_DIR/bin/python" -m pip install -r "$DEMOS_DIR/agent-accessible-workflows/requirements.txt"
  "$VENV_DIR/bin/python" -m pip install -r "$DEMOS_DIR/agent-contaminant-investigation/requirements.txt"
  "$VENV_DIR/bin/python" -m pip install -r "$DEMOS_DIR/repeatable-weekly-report/requirements-agent.txt"
  "$VENV_DIR/bin/python" -m pip install -r "$ROOT_DIR/requirements.txt"
fi

if [[ -x "$VENV_DIR/bin/python" ]]; then
  PY="$VENV_DIR/bin/python"
else
  PY="$PYTHON_BIN"
fi

STUDIES_DIR="$DEMOS_DIR/_shared_studies"
pids=()

cleanup() {
  echo
  echo "Stopping learning-loop services..."
  for pid in "${pids[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup INT TERM EXIT

start_service() {
  local name="$1"
  local workdir="$2"
  local port="$3"
  shift 3
  echo "Starting $name on port $port ..."
  (
    cd "$workdir"
    export PYTHONPATH="."
    for assignment in "$@"; do
      export "$assignment"
    done
    exec "$PY" -m uvicorn api.main:app --port "$port"
  ) &
  pids+=("$!")
}

start_service "DESeq API" "$DEMOS_DIR/agent-accessible-workflows/src" 8000 \
  "DESEQ_DEMO_MODE=true"

start_service "Contamination API" "$DEMOS_DIR/agent-contaminant-investigation/src" 8001 \
  "CONTAM_DEMO_MODE=true" \
  "ARTIFACT_STORAGE=filesystem"

start_service "Cycle report API" "$DEMOS_DIR/repeatable-weekly-report/src" 8002 \
  "REPORT_DEMO_MODE=true"

start_service "Orchestrator API" "$ROOT_DIR/src" 8003 \
  "ORCHESTRATOR_DEMO_MODE=true" \
  "DESEQ_API_BASE=http://127.0.0.1:8000" \
  "CONTAM_API_BASE=http://127.0.0.1:8001" \
  "REPORT_API_BASE=http://127.0.0.1:8002" \
  "STUDIES_DIR=$STUDIES_DIR"

echo
echo "Learning loop services are running. In another terminal:"
echo "  cd $ROOT_DIR && ./verify-demo.sh"
echo "Press Ctrl+C here to stop all four services."
wait
