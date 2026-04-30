---
layout: default
title: Residue contact map (synthetic)
description: Cα distance matrix from a compact chain; binary contacts at 8 Å.
banner_logo_right: true
---

## Scientific question

Which **residue pairs** are close in three dimensions—i.e. candidate **contacts**—for a folded chain?

## What we would conclude with this

Contact maps summarize **tertiary organization** without a full structural model; long-range contacts often separate **folded** from **extended** states in real analyses.

## Synthetic data

**72** residues; 3D coordinates from a **helical** path with noise; pairwise **Cα** distances stored as an edge list. **Seed: 42**. See `demos/scientific-structural-contacts/data/generate.py`.

## Approach

Rebuild the symmetric distance matrix; mark contacts where **distance ≤ 8 Å** and **|i − j| ≥ 2** (exclude immediate sequence neighbors).

## Key outputs

![Contact map]({{ '/demos/scientific-structural-contacts/outputs/contact_map.png' | relative_url }})

## Reproduce

{% include demo-source.html slug="scientific-structural-contacts" %}

```bash
cd demos/scientific-structural-contacts
python3 data/generate.py
python3 src/run.py
```

Dependencies: `demos/requirements.txt`.
