#!/usr/bin/env bash
# Regenerate outputs for the 12 simple portfolio demos (not agent-accessible-workflows).
# Requires Python 3.11+ with demos/requirements.txt installed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEMOS="$ROOT/demos"

PYTHON="${PORTFOLIO_PYTHON:-}"
if [[ -z "$PYTHON" ]]; then
  for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1 && "$cmd" -c 'import sys; assert sys.version_info[:2] >= (3, 11)' 2>/dev/null; then
      PYTHON="$cmd"
      break
    fi
  done
fi
[[ -n "$PYTHON" ]] || { echo "Python 3.11+ required. Set PORTFOLIO_PYTHON." >&2; exit 1; }
echo "Using $PYTHON"

SLUGS=(
  forecasting-uncertainty
  ab-testing-decisions
  segmentation-explainable
  margin-whatif
  multimodal-support-signals
  repeatable-weekly-report
  scientific-bioinformatics-de
  scientific-cheminformatics-similarity
  scientific-predictive-dose-response
  scientific-structural-contacts
  scientific-generative-sequences
  scientific-multimodal-biology
)

for slug in "${SLUGS[@]}"; do
  echo "=== $slug ==="
  cd "$DEMOS/$slug"
  "$PYTHON" data/generate.py
  "$PYTHON" src/run.py
done

echo "Done. Commit PNG/CSV files under demos/*/outputs/"
