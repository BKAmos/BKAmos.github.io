---
layout: default
title: Repeatable weekly report
description: Python + Jinja2 HTML report from synthetic weekly KPI CSVs.
banner_logo_right: true
---

## Cycle report agent (RNA-seq micro-loop)

In addition to the business weekly KPI report below, this demo folder includes a **cycle report sub-agent** used by the [RNA-seq trust-and-DE orchestrator]({% link portfolio/agent-learning-orchestrator.md %}). After each internal orchestrator cycle, it renders `cycle_report.html` and JSON from a cycle snapshot manifest.

- API: `POST /tools/run_cycle_report` (port **8002** in local stack)
- Template: `demos/repeatable-weekly-report/src/cycle_report.html.j2`
- See [repeatable-weekly-report README](https://github.com/BKAmos/BKAmos.github.io/blob/main/demos/repeatable-weekly-report/README.md) for agent API details

## Business question

Can we replace one-off spreadsheets with a **repeatable** weekly narrative: same structure, fresh numbers?

## What we would decide with this

Automate the **skeleton** of the report (tables, highlights) so stakeholders get consistent timing and definitions; humans still interpret and annotate in review.

## Synthetic data

Two CSVs: **weekly KPIs** (revenue, orders, returns) and a small **incidents** table. **Seed: 42**. See `demos/repeatable-weekly-report/data/generate.py`.

## Approach

`pandas` loads the CSVs; **Jinja2** renders `src/report.html.j2` using string tables in `src/strings_en.json` and `src/strings_es.json`. The script writes **English** and **Spanish** variants plus a default `report.html` (English copy).

## Key outputs

Open the generated files in a browser:

- [Report (English)]({{ '/demos/repeatable-weekly-report/outputs/report_en.html' | relative_url }})
- [Report (Spanish)]({{ '/demos/repeatable-weekly-report/outputs/report_es.html' | relative_url }})
- [Report (default)]({{ '/demos/repeatable-weekly-report/outputs/report.html' | relative_url }}) — same content as English

## Reproduce

{% include demo-source.html slug="repeatable-weekly-report" %}

```bash
cd demos/repeatable-weekly-report
python3 data/generate.py
python3 src/run.py
```

Dependencies: `demos/requirements.txt` (includes `jinja2`).
