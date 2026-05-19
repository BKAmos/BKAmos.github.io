# Agentic contamination investigation (local-first)

This demo adapts an agentic investigation workflow to triage possible foreign genetic material or contaminants in synthetic samples.

Surfaces:
- browser UI on the portfolio page,
- REST/CLI API for scripted usage,
- MCP-compatible gateway tools for agent workflows.

## Quickstart

### Windows

```powershell
cd demos\agent-contaminant-investigation
.\start-demo.ps1 -EnableQueue -WorkerScale 4
.\verify-demo.ps1 -CheckQueue
```

Run focused validation without starting the stack:

```powershell
cd demos\agent-contaminant-investigation
.\validate-demo.ps1
```

### macOS/Linux

```bash
cd demos/agent-contaminant-investigation
ENABLE_QUEUE=true WORKER_SCALE=4 ./start-demo.sh
CHECK_QUEUE=true ./verify-demo.sh
```

Run focused validation without starting the stack:

```bash
cd demos/agent-contaminant-investigation
./validate-demo.sh
```

## Synthetic profiles

- `clean`
- `low_contam`
- `high_contam`
- `edge_case`

Each run generates tables/logs, then the bounded investigation loop executes:
overview -> investigator plan -> guarded execution -> summary -> verdict review. The loop records each pass in `manifest.json`, stops early on a confident or stable verdict, and never runs more than three passes.

## Local Python run

```bash
cd demos/agent-contaminant-investigation
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 data/generate.py --profile low_contam --samples 24
python3 src/run.py
```

## API example

```bash
curl -X POST "http://localhost:8000/tools/run_investigation" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_TOKEN" \
  --data-binary @src/fixtures/run-deseq-synthetic.json
```

## Key outputs

- `manifest.json`
- `overview.json`
- `investigator_plan.json`
- `evidence.json`
- `summary.json`
- `verdict.json`
- `timeline.json`
- `top_non_host_taxa.png`
- `report.html`

## Artifact storage

The Docker stack wires generated run artifacts into MinIO by default:

- API and worker containers use `ARTIFACT_STORAGE=minio`.
- The API creates `MINIO_BUCKET` on first upload when needed.
- Browser and MCP clients still download artifacts through `/jobs/{job_id}/artifacts/{artifact_name}` so MinIO credentials stay server-side.
- Set `ARTIFACT_STORAGE=filesystem` in `src/.env` to keep artifacts only on the shared local run volume.

See `runbook-local.md` for multi-surface validation (UI + CLI + agent).
