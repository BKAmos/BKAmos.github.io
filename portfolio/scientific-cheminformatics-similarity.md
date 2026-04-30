---
layout: default
title: Compound similarity (synthetic)
description: Binary fingerprints and physicochemical-style descriptors without RDKit; Tanimoto similarity and PCA.
banner_logo_right: true
---

## Scientific question

Given a **query** compound and a library of **synthetic** structures, which neighbors are **structurally similar**, and how do compounds spread in **descriptor space**?

## What we would conclude with this

High **Tanimoto** overlap on fingerprints suggests analogs for SAR; **PCA** reveals scaffold clusters and outliers—useful for library design or hit expansion.

## Synthetic data

**120** compounds, **64-bit** binary fingerprints drawn from **three** scaffold families; **MW**, **logP**, and **TPSA**-like columns derived from fingerprint density and cluster. **Seed: 42**. See `demos/scientific-cheminformatics-similarity/data/generate.py`. **No RDKit**—pure NumPy/Pandas.

## Approach

**Tanimoto** coefficient on bit vectors; **PCA** (`scikit-learn`) for a 2D embedding; dual coloring by cluster and by similarity to **CMP-000**.

## Key outputs

![PCA landscape]({{ '/demos/scientific-cheminformatics-similarity/outputs/pca_landscape.png' | relative_url }})

## Reproduce

{% include demo-source.html slug="scientific-cheminformatics-similarity" %}

```bash
cd demos/scientific-cheminformatics-similarity
python3 data/generate.py
python3 src/run.py
```

Dependencies: `demos/requirements.txt`.
