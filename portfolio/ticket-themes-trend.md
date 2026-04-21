---
layout: default
title: Ticket themes over time
description: Synthetic support tickets bucketed by theme with weekly volume trends.
banner_logo_right: true
---

## Business question

Which themes drive support volume, and are any themes trending up in recent weeks?

## What we would decide with this

Prioritize **product**, **documentation**, or **ops** work on themes with high volume or a rising trend; deprioritize noise categories that stay flat.

## Synthetic data

Synthetic ticket subjects and bodies with assigned **theme** labels and **week** indices. **Seed: 42**. See `demos/ticket-themes-trend/data/generate.py`.

## Approach

Aggregate counts by week and theme; plot a **stacked area** of weekly volumes (lightweight, interpretable—no extra NLP stack).

## Key outputs

![Weekly ticket volume by theme]({{ '/demos/ticket-themes-trend/outputs/ticket_themes.png' | relative_url }})

## Reproduce

{% include demo-source.html slug="ticket-themes-trend" %}

```bash
cd demos/ticket-themes-trend
python3 data/generate.py
python3 src/run.py
```

Dependencies: `demos/requirements.txt`.
