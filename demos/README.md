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
| `ticket-themes-trend` | Weekly theme volumes |
| `repeatable-weekly-report` | Jinja2 HTML report |
