# Local runbook

## 1) Start stack

```powershell
cd demos\agent-contaminant-investigation
.\start-demo.ps1 -EnableQueue -WorkerScale 4
```

## 2) Verify API + queue

```powershell
cd demos\agent-contaminant-investigation
.\verify-demo.ps1 -CheckQueue
```

For stack-free regression checks, run focused scoring/API tests and the gateway typecheck:

```powershell
cd demos\agent-contaminant-investigation
.\validate-demo.ps1
```

Artifacts are uploaded to MinIO when `ARTIFACT_STORAGE=minio` in `src/.env`.
The API keeps serving downloads through `/jobs/{job_id}/artifacts/{artifact_name}`.
You can inspect the MinIO console at `http://localhost:9001` with the `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` values from `src/.env`.

## 3) UI surface

Run Jekyll from repo root and open:
- `http://127.0.0.1:4000/portfolio/agent-contaminant-investigation.html`

Paste `API_TOKEN` from `demos/agent-contaminant-investigation/src/.env`, submit a run, and confirm stage timeline + verdict populate.

## 4) CLI surface

```powershell
cd demos\agent-contaminant-investigation\src
.\submit-parallel-jobs.ps1 -Count 8
```

## 5) Agent surface

From `demos/agent-contaminant-investigation/src/gateway`:

```powershell
npx wrangler dev
npx @modelcontextprotocol/inspector
```

In MCP Inspector (`http://127.0.0.1:8787/mcp`):
1. `tools/list`
2. `tools/call` -> `run_investigation`
3. `tools/call` -> `get_status`
4. `tools/call` -> `get_summary`

## 6) Done criteria

- API returns `{"status":"ok"}`.
- UI run reaches `completed` and shows evidence + verdict.
- Queue submissions return `queued` when `ENABLE_RQ=true`.
- Worker logs show jobs distributed across replicas.
- MCP tools can submit and retrieve run summaries.
