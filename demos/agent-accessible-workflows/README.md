# Agent-accessible DESeq workflow

Functional portfolio demo for running a toy DESeq-style differential expression workflow through three surfaces:

- browser UI on the portfolio page,
- REST API for power users,
- Cloudflare Worker MCP tools for agents.

The included dataset is synthetic and safe to publish. It exists to test the full architecture, not to support biological conclusions. This demo does not accept user uploads: UX, CLI/API calls, and MCP tools all run synthetic-only jobs.

For a copy-paste local validation flow (including queue + UX/CLI/agent concurrency), see `runbook-local.md`.

## Quickstart (Track B local package)

### Windows (PowerShell)

```powershell
cd demos\agent-accessible-workflows
.\start-demo.ps1
.\verify-demo.ps1
```

Queue + concurrency mode:

```powershell
cd demos\agent-accessible-workflows
.\start-demo.ps1 -EnableQueue -WorkerScale 4
.\verify-demo.ps1 -CheckQueue
```

### macOS / Linux

```bash
cd demos/agent-accessible-workflows
chmod +x start-demo.sh verify-demo.sh
./start-demo.sh
./verify-demo.sh
```

Queue + concurrency mode:

```bash
cd demos/agent-accessible-workflows
ENABLE_QUEUE=true WORKER_SCALE=4 ./start-demo.sh
CHECK_QUEUE=true ./verify-demo.sh
```

`start-demo` creates `src/.env` from `.env.example` if needed, generates an `API_TOKEN` if placeholder values are present, and starts Docker services.

## Synthetic workload profiles

`run_deseq` accepts bounded profiles to keep compute noticeable but controlled:

- `small`: 1,000 genes x 12 samples
- `medium`: 5,000 genes x 24 samples
- `large`: 10,000 genes x 32 samples

Optional: set `synthetic_seed` for reproducible variation.

## Local Python run

```bash
cd demos/agent-accessible-workflows
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 data/generate.py
python3 src/run.py
```

**Larger synthetic matrix (local stress test):** `python3 data/generate.py --genes 20000 --samples 48` (optional `--n-de 800`). Regenerates `data/counts.csv` and `metadata.csv`. For Docker, rebuild the API and worker images so the new files are copied into the image (`cd src && docker compose build api worker && docker compose up -d`).

Outputs are written to `outputs/`:

- `original_counts.csv`
- `results.csv`
- `top_genes.csv`
- `normalized_counts.csv`
- `metadata.csv`
- `volcano.png`
- `ma.png`
- `pca.png`
- `top_genes_heatmap.png`
- `report.html`
- `manifest.json`

## API smoke test

### Bash (Linux / macOS / Git Bash)

```bash
cd demos/agent-accessible-workflows
source .venv/bin/activate
PYTHONPATH=src uvicorn api.main:app --reload
```

Then in another shell (with the API running). **Docker Compose sets `DESEQ_DEMO_MODE` false by default**, so send a Bearer token that matches `API_TOKEN` in `src/.env`:

```bash
cd demos/agent-accessible-workflows/src
set -a
# shellcheck source=/dev/null
source .env
set +a
curl -sS -X POST "http://localhost:8000/tools/run_deseq" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_TOKEN" \
  --data-binary @fixtures/run-deseq-synthetic.json
```

For a one-off local uvicorn run with **demo mode** (no Bearer required), start with `DESEQ_DEMO_MODE=true` and you can omit the `Authorization` header.

### Windows PowerShell

From `demos/agent-accessible-workflows/src`, **do not** paste JSON on the `curl.exe -d` line: PowerShell parses `"` and `\` differently from Bash, which breaks the request body. Use either:

**Option A — helper script (recommended):**

```powershell
cd demos\agent-accessible-workflows\src
.\smoke-test.ps1
```

**Option B — `curl.exe` with a JSON file (no quoting issues):**

```powershell
cd demos\agent-accessible-workflows\src
$token = (Get-Content .env | ForEach-Object { if ($_ -match '^\s*API_TOKEN=(.*)$') { $matches[1].Trim() } } | Select-Object -First 1)
curl.exe -sS -X POST "http://localhost:8000/tools/run_deseq" `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $token" `
  --data-binary "@fixtures\run-deseq-synthetic.json"
```

Use **`--data-binary @file`**, not `-d` with an inline JSON string, when calling `curl.exe` from PowerShell.

Example inline payload (CLI/API) for a heavier synthetic run:

```json
{
  "dataset": "synthetic",
  "synthetic_profile": "large",
  "condition_column": "condition",
  "reference_level": "control",
  "treatment_level": "treated",
  "batch_column": "batch",
  "min_count": 10
}
```

Copy `.env.example` to `.env` and set `API_TOKEN` before running Compose or `smoke-test.ps1`.

## Docker Compose

```bash
cd demos/agent-accessible-workflows/src
cp .env.example .env
# edit .env — set API_TOKEN
docker compose --env-file .env up --build
```

Services:

- API: `http://localhost:8000`
- Redis: internal queue
- Worker: RQ worker running PyDESeq2 jobs
- MinIO: `http://localhost:9001` for local object-storage parity

Windows: after the stack is up, run `.\smoke-test.ps1` from this directory (see **API smoke test**).

### Parallel jobs (Redis queue + multiple workers)

By default the API runs each DESeq job **inline** in the request (no queue). To stress **several worker containers** at once:

1. In **`src/.env`** set **`ENABLE_RQ=true`** (and keep **`API_TOKEN`** set).
2. Start or recreate the stack with extra worker replicas, e.g.:
   ```bash
   cd demos/agent-accessible-workflows/src
   docker compose --env-file .env up -d --build --scale worker=4
   ```
3. Submit concurrent jobs from PowerShell:
   ```powershell
   .\submit-parallel-jobs.ps1 -Count 8
   ```
   Each response should show **`"status":"queued"`**; poll **`GET /jobs/{job_id}`** until **`completed`**. With **N** workers, up to **N** runs execute at once.

The RQ job target is **`jobqueue.worker_loop.run_queued_deseq_job`** (this fixes an older enqueue path that pointed at a missing module).

### Concurrent multi-surface drill (UX + CLI + agent at once)

Use this to demonstrate backend containerization and multi-job execution across all three surfaces at the same time.

1. Enable queue mode and scale workers:
   ```bash
   cd demos/agent-accessible-workflows/src
   # in .env: ENABLE_RQ=true and API_TOKEN=<same token used by UI + gateway>
   docker compose --env-file .env up -d --build --scale worker=4
   ```
2. In one terminal, watch worker activity:
   ```bash
   cd demos/agent-accessible-workflows/src
   docker compose logs -f worker
   ```
3. Start API load from CLI:
   ```powershell
   cd demos\agent-accessible-workflows\src
   .\submit-parallel-jobs.ps1 -Count 8
   ```
4. Submit one or more UI jobs from the portfolio page while the CLI jobs are running.
5. Submit agent jobs through the Worker proxy at the same time (PowerShell file payload avoids quoting issues):
   ```powershell
   cd demos\agent-accessible-workflows\src
   @'
   {
     "dataset": "synthetic",
     "synthetic_profile": "large",
     "condition_column": "condition",
     "reference_level": "control",
     "treatment_level": "treated",
     "min_count": 10
   }
   '@ | Set-Content -Path .\tmp-agent-run.json -Encoding utf8
   $token = (Get-Content .env | ForEach-Object { if ($_ -match '^\s*API_TOKEN=(.*)$') { $matches[1].Trim() } } | Select-Object -First 1)
   curl.exe -sS -X POST "http://127.0.0.1:8787/api/tools/run_deseq" `
     -H "Content-Type: application/json" `
     -H "Authorization: Bearer $token" `
     --data-binary "@tmp-agent-run.json"
   ```

Expected behavior with queue mode enabled:
- each submission returns **`"status":"queued"`** with a unique `job_id`
- up to **N** jobs run concurrently when **N** worker containers are available
- worker logs show jobs being picked up across replicas (`worker-1`, `worker-2`, etc.)
- UI results render only when that specific UI-submitted job returns `completed`

## Cloudflare MCP gateway

See `src/gateway/README.md` for Wrangler deployment and MCP Inspector examples.

## Oracle Cloud

See `src/oracle-cloud/README.md` for Terraform and cloud-init deployment notes for an Always-Free A1 VM.
