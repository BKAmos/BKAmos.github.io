---
layout: default
title: Multimodal biological samples
description: Expression, imaging-style features, and clinical covariates linked by canonical correlation analysis.
banner_logo_right: true
---

## Scientific question

Do **molecular** readouts (expression + simple clinical context) **co-vary** with **imaging-derived** features in a way that separates sample groups?

## What we would conclude with this

**CCA** finds linear combinations of each modality that maximize cross-correlation—useful for **joint visualization** and hypothesis generation before heavier multimodal models.

## Synthetic data

**80** samples; **10** “genes,” **3** imaging metrics, **age** and **sex**; a hidden axis drives both blocks. **Seed: 42**. See `demos/scientific-multimodal-biology/data/generate.py`.

## Approach

Standardize blocks; **two-component CCA** (`sklearn.cross_decomposition.CCA`); scatter canonical scores colored by group.

## Key outputs

![CCA scatter]({{ '/demos/scientific-multimodal-biology/outputs/cca_scatter.png' | relative_url }})

## Reproduce

{% include demo-source.html slug="scientific-multimodal-biology" %}

```bash
cd demos/scientific-multimodal-biology
python3 data/generate.py
python3 src/run.py
```

Dependencies: `demos/requirements.txt`.
