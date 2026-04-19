---
layout: default
title: Margin what-if
description: Price and cost sensitivity using simple elasticity-style scenarios on synthetic units sold.
banner_logo_right: true
---

## Business question

If we adjust price or underlying cost, what happens to **margin** under a few plausible demand responses?

## What we would decide with this

Use the scenario table to stress-test **gross margin** before committing to pricing or procurement changes; pair with real elasticity estimates when available (here: illustrative constants only).

## Synthetic data

A baseline price, unit cost, and “base” volume are fixed; scenarios vary **price change** and **elasticity** (constant elasticity of demand). **Seed: 42** for any stochastic piece; see `demos/margin-whatif/data/generate.py`.

## Approach

For each scenario: \(Q = Q_0 \cdot (P/P_0)^{\epsilon}\), **revenue** \(P \cdot Q\), **margin** \((P - c) \cdot Q\). Plot margin by scenario index and export a CSV summary.

## Key outputs

![Margin by scenario]({{ '/demos/margin-whatif/outputs/margin_scenarios.png' | relative_url }})

## Reproduce

{% include demo-source.html slug="margin-whatif" %}

```bash
cd demos/margin-whatif
python3 data/generate.py
python3 src/run.py
```

Dependencies: `demos/requirements.txt`.
