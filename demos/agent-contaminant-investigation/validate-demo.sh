#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GATEWAY_DIR="$ROOT_DIR/src/gateway"
SKIP_GATEWAY_INSTALL="${SKIP_GATEWAY_INSTALL:-false}"

cd "$ROOT_DIR"
echo "Running Python validation tests..."
python3 -m pytest tests

cd "$GATEWAY_DIR"
if [[ "$SKIP_GATEWAY_INSTALL" != "true" && ! -d node_modules ]]; then
  echo "Installing gateway dependencies with npm ci..."
  npm ci
fi

echo "Running gateway typecheck..."
npm run typecheck

echo ""
echo "Validation complete."
