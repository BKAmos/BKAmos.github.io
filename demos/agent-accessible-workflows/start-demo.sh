#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$ROOT_DIR/src"
ENV_PATH="$SRC_DIR/.env"
ENV_EXAMPLE_PATH="$SRC_DIR/.env.example"
ENABLE_QUEUE="${ENABLE_QUEUE:-false}"
WORKER_SCALE="${WORKER_SCALE:-2}"

if [[ ! -f "$ENV_PATH" ]]; then
  cp "$ENV_EXAMPLE_PATH" "$ENV_PATH"
  echo "Created $ENV_PATH from .env.example"
fi

current_token="$(rg '^API_TOKEN=' "$ENV_PATH" -n -N | sed 's/^API_TOKEN=//' || true)"
if [[ -z "${current_token:-}" || "$current_token" == "change-me-to-a-long-random-secret" || "$current_token" == "dev-token" ]]; then
  if command -v openssl >/dev/null 2>&1; then
    token="$(openssl rand -base64 36 | tr -d '\n' | tr '/+' 'AZ' | cut -c1-48)"
  else
    token="$(python3 - <<'PY'
import secrets, string
chars = string.ascii_letters + string.digits
print("".join(secrets.choice(chars) for _ in range(48)))
PY
)"
  fi
  if rg '^API_TOKEN=' "$ENV_PATH" >/dev/null 2>&1; then
    sed -i.bak "s|^API_TOKEN=.*|API_TOKEN=$token|" "$ENV_PATH"
  else
    printf "\nAPI_TOKEN=%s\n" "$token" >> "$ENV_PATH"
  fi
  rm -f "$ENV_PATH.bak"
  current_token="$token"
  echo "Generated API_TOKEN in src/.env"
fi

if rg '^ENABLE_RQ=' "$ENV_PATH" >/dev/null 2>&1; then
  sed -i.bak "s|^ENABLE_RQ=.*|ENABLE_RQ=$ENABLE_QUEUE|" "$ENV_PATH"
else
  printf "\nENABLE_RQ=%s\n" "$ENABLE_QUEUE" >> "$ENV_PATH"
fi
rm -f "$ENV_PATH.bak"

cd "$SRC_DIR"
if [[ "$ENABLE_QUEUE" == "true" ]]; then
  docker compose --env-file .env up -d --build --scale "worker=$WORKER_SCALE"
else
  docker compose --env-file .env up -d --build
fi
docker compose ps

echo ""
echo "Demo is up."
echo "API health: http://localhost:8000/healthz"
echo "Run smoke test: cd demos/agent-accessible-workflows && ./verify-demo.sh"
echo "Portfolio page (if Jekyll running): http://127.0.0.1:4000/portfolio/agent-accessible-workflows.html"
echo "API_TOKEN (use for UI/CLI/gateway): $current_token"
