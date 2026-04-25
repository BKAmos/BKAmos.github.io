# Agent-accessible DESeq workflow

Functional portfolio demo for running a toy DESeq-style differential expression workflow through three surfaces:

- browser UI on the portfolio page,
- REST API for power users,
- Cloudflare Worker MCP tools for agents.

The included dataset is synthetic and safe to publish. It exists to test the full architecture, not to support biological conclusions.

## Local Python run

```bash
cd demos/agent-accessible-workflows
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 data/generate.py
python3 src/run.py
```

Outputs are written to `outputs/`:

- `results.csv`
- `top_genes.csv`
- `normalized_counts.csv`
- `volcano.png`
- `ma.png`
- `pca.png`
- `top_genes_heatmap.png`
- `report.html`
- `manifest.json`

## API smoke test

```bash
cd demos/agent-accessible-workflows
source .venv/bin/activate
PYTHONPATH=src uvicorn api.main:app --reload
```

Then in another shell:

```bash
curl -X POST http://localhost:8000/tools/run_deseq \
  -H "Content-Type: application/json" \
  -d '{"dataset":"synthetic","condition_column":"condition","reference_level":"control","treatment_level":"treated","min_count":10}'
```

Set `DESEQ_DEMO_MODE=false` and `API_TOKEN=<token>` to require `Authorization: Bearer <token>`.

## Docker Compose

```bash
cd demos/agent-accessible-workflows/src
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- Redis: internal queue
- Worker: RQ worker running PyDESeq2 jobs
- MinIO: `http://localhost:9001` for local object-storage parity

## Cloudflare MCP gateway

See `src/gateway/README.md` for Wrangler deployment and MCP Inspector examples.

## Oracle Cloud

See `src/oracle-cloud/README.md` for Terraform and cloud-init deployment notes for an Always-Free A1 VM.
