---
layout: default
title: Repeatable weekly report
description: Python + Jinja2 HTML report from synthetic weekly KPI CSVs.
banner_logo_right: true
---

## Business question

Can we replace one-off spreadsheets with a **repeatable** weekly narrative: same structure, fresh numbers?

## What we would decide with this

Automate the **skeleton** of the report (tables, highlights) so stakeholders get consistent timing and definitions; humans still interpret and annotate in review.

## Synthetic data

Two CSVs: **weekly KPIs** (revenue, orders, returns) and a small **incidents** table. **Seed: 42**. See `demos/repeatable-weekly-report/data/generate.py`.

## Approach

`pandas` loads the CSVs; **Jinja2** renders `src/report.html.j2` into `outputs/report.html` (self-contained HTML suitable to open locally or publish as an artifact).

## Key outputs

Open the generated file in a browser: [sample report HTML]({{ '/demos/repeatable-weekly-report/outputs/report.html' | relative_url }}) (static file in this repo).

## Reproduce

{% include demo-source.html slug="repeatable-weekly-report" %}

```bash
cd demos/repeatable-weekly-report
python3 data/generate.py
python3 src/run.py
```

Dependencies: `demos/requirements.txt` (includes `jinja2`).
