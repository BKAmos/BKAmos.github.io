# Repeatable weekly report (HTML)

Synthetic KPI and incident CSVs rendered with Jinja2 to **`outputs/report_en.html`**, **`outputs/report_es.html`**, and **`outputs/report.html`** (English copy).

## Business weekly report

```bash
python3 data/generate.py
python3 src/run.py
```

UI strings live in `src/strings_en.json` and `src/strings_es.json`; numeric highlight sentences are built in `run.py` per locale.

## Cycle report agent (RNA-seq micro-loop)

A minimal FastAPI surface for the [agent-learning-orchestrator](../agent-learning-orchestrator/) component. Renders per-cycle HTML + JSON from an orchestrator snapshot — does not replace the business weekly report above.

### Start API (local)

```powershell
cd demos\repeatable-weekly-report\src
$env:PYTHONPATH="."
$env:REPORT_DEMO_MODE="true"
uvicorn api.main:app --port 8002
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/healthz` | Health check |
| `POST` | `/tools/run_cycle_report` | Body: `{ "cycle_snapshot": { ... } }` → job id + artifacts |
| `GET` | `/jobs/{job_id}` | Job manifest |
| `GET` | `/jobs/{job_id}/artifacts/cycle_report.html` | Rendered HTML report |

Template: `src/cycle_report.html.j2`. Worker logic: `src/run_cycle_report.py`.

### Tests

```bash
cd demos/repeatable-weekly-report
pip install -r requirements-agent.txt
PYTHONPATH=src pytest tests/ -q
```

**Python 3.11+** recommended; API uses `typing_extensions.Annotated` and `Optional[...]` in Pydantic models for 3.8 compatibility.

Dependencies: `requirements-agent.txt` (FastAPI, Jinja2, pytest).
