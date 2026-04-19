---
layout: default
title: Customer and product segmentation
description: K-means clusters with readable segment profiles on synthetic attributes.
banner_logo_right: true
---

## Business question

Which natural groups exist among customers (or products), and how do they differ on behaviors we can act on?

## What we would decide with this

Assign each unit to a **segment**, then tailor messaging, assortment, or support using the **profile** (average features per cluster). Revisit when data or strategy shifts.

## Synthetic data

Rows are synthetic customers with features such as annual spend, visit frequency, and tenure. **Seed: 42**. See `demos/segmentation-explainable/data/generate.py`.

## Approach

**K-means** (`scikit-learn`, k=3); features scaled with **StandardScaler**. Segment profiles: cluster centers in original feature space (inverse transform) plus a 2D PCA scatter for visualization.

## Key outputs

![Segments in PCA space and profile heatmap]({{ '/demos/segmentation-explainable/outputs/segmentation.png' | relative_url }})

## Reproduce

{% include demo-source.html slug="segmentation-explainable" %}

```bash
cd demos/segmentation-explainable
python3 data/generate.py
python3 src/run.py
```

Dependencies: `demos/requirements.txt`.
