# Local Runbook (Track B)

This runbook is the fast, repeatable proof-of-concept flow for local execution across all three surfaces:

- UX (portfolio page)
- CLI (PowerShell scripts)
- Agent interface (MCP Inspector or Worker proxy)

Use it for demos, screenshots, and release validation.

## 0) Prerequisites

- Docker Desktop running
- PowerShell 5.1+ (Windows) or Bash (macOS/Linux)
- Optional for UX page: Jekyll (`bundle exec jekyll serve --livereload`)
- Optional for MCP: Wrangler dev (`npx wrangler dev`) from `src/gateway`

## 1) Start stack

From repo root:

```powershell
cd demos\agent-accessible-workflows
.\start-demo.ps1 -EnableQueue -WorkerScale 4
```

Expected:

- API health URL prints: `http://localhost:8000/healthz`
- `docker compose ps` shows `api`, `redis`, `minio`, and multiple `worker` containers up
- token is printed as `API_TOKEN (...)`

## 2) Verify baseline health

```powershell
cd demos\agent-accessible-workflows
.\verify-demo.ps1 -CheckQueue
```

Expected:

- Health check passed
- Smoke run returns a `job_id`
- Queue check returns responses that include `status: queued` when `ENABLE_RQ=true`

## 3) Open UI surface

Start Jekyll from repo root (new terminal):

```powershell
cd E:\Github\BKAmos.github.io
bundle exec jekyll serve --livereload
```

Open:

- `http://127.0.0.1:4000/portfolio/agent-accessible-workflows.html`

In UI:

- Paste `API_TOKEN` into API token field
- Submit one run (`medium` or `large`)

Expected:

- Job ID appears in UI
- Status moves from queued/running to completed
- Results panel remains hidden until completion
- Run-specific links/images/CSV preview appear only after job completes

## 4) Start CLI concurrent load

In another terminal:

```powershell
cd demos\agent-accessible-workflows\src
.\submit-parallel-jobs.ps1 -Count 8
```

Expected:

- Multiple responses with unique `job_id`
- With queue enabled, initial status is `queued`

## 5) Start agent surface during load

Pick one option.

### Option A: MCP Inspector (recommended)

From `demos/agent-accessible-workflows/src/gateway`:

```powershell
npx wrangler dev
```

In separate terminal:

```powershell
npx @modelcontextprotocol/inspector
```

Connect Inspector to:

- URL: `http://127.0.0.1:8787/mcp`
- Transport: `streamable-http`

Then run:

1. `tools/list`
2. `tools/call` -> `run_deseq` with `dataset=synthetic` and `synthetic_profile=large`
3. `tools/call` -> `get_job_status` with returned `job_id`

### Option B: Worker proxy API path

```powershell
cd demos\agent-accessible-workflows\src
$token = (Get-Content .env | ForEach-Object { if ($_ -match '^\s*API_TOKEN=(.*)$') { $matches[1].Trim() } } | Select-Object -First 1)
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
curl.exe -sS -X POST "http://127.0.0.1:8787/api/tools/run_deseq" `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $token" `
  --data-binary "@tmp-agent-run.json"
```

Expected:

- Response returns `job_id` (and queued status when queue mode is enabled)

## 6) Observe backend concurrency

In a monitoring terminal:

```powershell
cd demos\agent-accessible-workflows\src
docker compose logs -f worker
```

Expected:

- jobs consumed across multiple worker containers
- interleaved processing confirms multi-job execution

Optional memory monitor:

```powershell
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.PIDs}}"
```

## 7) Pass/fail criteria (Definition of Done)

Pass when all are true:

- API health endpoint returns `{"status":"ok"}`
- CLI smoke run succeeds and returns job ID
- Queue submissions return `queued` (when `ENABLE_RQ=true`)
- UI run completes and renders only run-specific results
- Agent submission returns job ID and status can be polled
- Worker logs show concurrent processing on multiple containers

Fail examples:

- 401 from UI/API (token mismatch)
- parse errors from inline PowerShell JSON (use `--data-binary @file`)
- MCP errors due to gateway not running or bad DO migration config

## 8) Screenshot checklist (portfolio evidence)

Capture these artifacts:

1. `docker compose ps` with scaled workers
2. CLI parallel output (`submit-parallel-jobs.ps1`)
3. UI showing submitted job ID + completed status
4. UI results section with run-specific artifact links/images
5. MCP Inspector `run_deseq` + `get_job_status` responses
6. Worker logs showing concurrent jobs across worker replicas

## 9) Cleanup

```powershell
cd demos\agent-accessible-workflows\src
docker compose down
```

Optional full cleanup (includes volumes):

```powershell
docker compose down -v
```
