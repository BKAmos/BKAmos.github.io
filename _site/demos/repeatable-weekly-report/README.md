# Repeatable weekly report (HTML)

Synthetic KPI and incident CSVs rendered with Jinja2 to **`outputs/report_en.html`**, **`outputs/report_es.html`**, and **`outputs/report.html`** (English copy).

```bash
python3 data/generate.py
python3 src/run.py
```

UI strings live in `src/strings_en.json` and `src/strings_es.json`; numeric highlight sentences are built in `run.py` per locale.
