# Portfolio demos (Python)

Synthetic-data examples that pair with the Jekyll **Portfolio** section. Each folder under `demos/` contains a generator, analysis script, and checked-in outputs used by the site.

## Setup

Python **3.11+** recommended (see repo `.ruby-version` for Jekyll only; Python version is not pinned in this repo—use your system or `pyenv`).

```bash
cd demos
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run one demo

```bash
cd demos/<demo-slug>
python3 data/generate.py
python3 src/run.py
```

Artifacts are written to `outputs/` (and sometimes `data/*.csv`). The portfolio pages embed files from `outputs/` via site-relative URLs.

## Demos

| Slug | Topic |
|------|--------|
| `forecasting-uncertainty` | Demand forecast + interval |
| `ab-testing-decisions` | Two-sample inference |
| `segmentation-explainable` | K-means + profiles |
| `margin-whatif` | Price/cost scenarios |
| `multimodal-support-signals` | Text + tabular fusion, k-means, weekly mix |
| `repeatable-weekly-report` | Jinja2 HTML report (EN + ES) + optional cycle report agent API |
| `agent-accessible-workflows` | DESeq UI + MCP/API workflow with synthetic RNA-seq |
| `agent-contaminant-investigation` | Agentic contamination triage with guarded evidence workflow |
| `agent-learning-orchestrator` | RNA-seq trust-and-DE micro-loop (Contamination → DESeq → Report → handoff) |
| `scientific-bioinformatics-de` | Toy DE + volcano (BH-FDR) |
| `scientific-cheminformatics-similarity` | Fingerprints + Tanimoto + PCA (no RDKit) |
| `scientific-predictive-dose-response` | Hill fit + bootstrap band |
| `scientific-structural-contacts` | Synthetic Cα distances + contact map |
| `scientific-generative-sequences` | PWM + latent motif strength |
| `scientific-multimodal-biology` | Expression + imaging + clinical CCA |

`agent-accessible-workflows`, `agent-contaminant-investigation`, and `agent-learning-orchestrator` have their own `requirements.txt` files because their API/queue stacks are heavier than the shared plotting/science dependencies above.

## Agentic component model

The **agent-learning-orchestrator** demo is a composable micro-loop: it delegates to contamination, DESeq, and cycle-report sub-agents, runs ≤3 internal reflect/adapt cycles, and emits [`component_summary.json`](agent-learning-orchestrator/outputs/component_summary.json) for a future parent orchestrator. Schema: [`agent-learning-orchestrator/COMPONENT_SUMMARY_SCHEMA.md`](agent-learning-orchestrator/COMPONENT_SUMMARY_SCHEMA.md). Sub-agents remain independently runnable.
