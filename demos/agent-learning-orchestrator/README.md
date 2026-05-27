# RNA-seq trust-and-DE micro-loop component

Minimal agent-orchestrated learning loop for the SciAna portfolio:

**Contamination QC → DESeq → cycle report → reflect/adapt (≤3 internal cycles) → `component_summary.json` handoff**

This component is designed to plug into a **larger parent orchestrator** later. It does not route to multimodal, dose-response, or other portfolio demos.

## Sub-agents

| Agent | Default port | Demo folder |
|-------|--------------|-------------|
| DESeq | 8000 | `demos/agent-accessible-workflows` |
| Contamination | 8001 | `demos/agent-contaminant-investigation` |
| Cycle report | 8002 | `demos/repeatable-weekly-report` |
| **This orchestrator** | **8003** | `demos/agent-learning-orchestrator` |

## Python version

**Python 3.11+** is recommended (matches CI). The API layer is kept compatible with **Python 3.8** where practical: use `typing_extensions.Annotated`, `Optional[...]` in Pydantic models (not `|`), and the `__package__ in {None, "", "api"}` import pattern when running `uvicorn api.main:app` from `src/`.

## Quickstart

### Option A — full learning-loop launcher

Use this path for the MVP local demo. It starts all four APIs with host `uvicorn` processes so every service can read the same shared study bundle under `demos/_shared_studies`.

```powershell
cd demos\agent-learning-orchestrator
.\start-learning-loop.ps1 -Install
.\verify-demo.ps1
```

```bash
cd demos/agent-learning-orchestrator
INSTALL_DEPS=true ./start-learning-loop.sh
./verify-demo.sh
```

Docker Compose remains available for the standalone DESeq and contamination demos, but the orchestration MVP uses host processes by default to avoid host/container `inputs_dir` path mismatches.

### Option B — manual startup

#### 1. Start sub-agents (three terminals)

```powershell
# Terminal A — DESeq (port 8000)
cd demos\agent-accessible-workflows\src
$env:PYTHONPATH="."
$env:DESEQ_DEMO_MODE="true"
uvicorn api.main:app --port 8000

# Terminal B — Contamination (port 8001)
cd demos\agent-contaminant-investigation\src
$env:PYTHONPATH="."
$env:CONTAM_DEMO_MODE="true"
uvicorn api.main:app --port 8001

# Terminal C — Report (port 8002)
cd demos\repeatable-weekly-report\src
$env:PYTHONPATH="."
$env:REPORT_DEMO_MODE="true"
uvicorn api.main:app --port 8002
```

#### 2. Start orchestrator

```powershell
cd demos\agent-learning-orchestrator
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
cd src
$env:PYTHONPATH="."
$env:ORCHESTRATOR_DEMO_MODE="true"
$env:DESEQ_API_BASE="http://127.0.0.1:8000"
$env:CONTAM_API_BASE="http://127.0.0.1:8001"
$env:REPORT_API_BASE="http://127.0.0.1:8002"
uvicorn api.main:app --port 8003
```

#### 3. Run a component

PowerShell strips `"` from arguments passed to native programs like `curl.exe`, so bash-style `-d "{\"key\": 3}"` and even `-d '{"key": 3}'` both arrive as invalid JSON. Use one of these:

```powershell
# Option A — Invoke-RestMethod (recommended in PowerShell)
Invoke-RestMethod -Method POST `
  -Uri "http://127.0.0.1:8003/tools/start_component" `
  -ContentType "application/json" `
  -Body '{"max_internal_cycles": 3}'

# Option B — curl.exe with stop-parsing (--% passes the rest of the line through unchanged)
curl.exe --% -sS -X POST http://127.0.0.1:8003/tools/start_component -H "Content-Type: application/json" -d "{\"max_internal_cycles\": 3}"
```

Poll summary:

```powershell
curl.exe -sS "http://127.0.0.1:8003/components/<component_run_id>/summary"
```

## Learning signals

- **Shared cohort** — orchestrator writes one study bundle to `demos/_shared_studies/{study_id}/` (override with `STUDIES_DIR`) and passes `inputs_dir` to contamination and DESeq
- **Contamination gate** — DE runs only when verdict is `no_strong_contamination_signal`
- **DE adaptation** — relaxes `min_count` or changes `synthetic_profile` when hits are empty or unstable
- **Stability check** — Jaccard overlap on top-10 genes between consecutive internal cycles (threshold 0.5)

## MCP gateway

See `src/gateway/` for Cloudflare Worker MCP tools: `start_component`, `get_component_status`, `get_component_summary`, `submit_to_parent`.

## Tests

```bash
cd demos/agent-learning-orchestrator
pip install -r requirements.txt
PYTHONPATH=src pytest tests/ -q
```

See `runbook-local.md` for validation checklist.

Handoff schema: [`COMPONENT_SUMMARY_SCHEMA.md`](COMPONENT_SUMMARY_SCHEMA.md). End-to-end smoke: `./verify-demo.sh` or `.\verify-demo.ps1` (orchestrator on port 8003).
