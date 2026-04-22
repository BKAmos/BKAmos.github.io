---
layout: default
title: Generative sequences (PWM + latent)
description: Classical DNA motif PWM plus a 2D latent decoder that modulates motif strength; scores and interpolation.
banner_logo_right: true
---

## Scientific question

Can we **propose sequences** whose motif content is **tunable**—here combining a **PWM** with a simple **latent** “strength” decoder—and track that change along an **interpolation** path?

## What we would conclude with this

**PWM sampling** gives an interpretable generative baseline; **latent mixing** between PWM and background mimics how deep models might **smoothly vary** motif usage. This is a **toy** illustration, not a trained genome-scale generative model.

## Synthetic data

A **12 bp** DNA PWM (CSV) and a **background** base composition; sequences are **40 bp** with a fixed motif window. **Seed: 42** (data), **7** (sampling). See `demos/scientific-generative-sequences/data/generate.py` and `src/run.py`.

## Approach

1. **Classical:** sample motif positions from row-wise PWM; negatives use background only.  
2. **Latent:** map **z ∈ ℝ²** through a logistic decoder to **strength s(z) ∈ (0,1)**; per-position probabilities are **s·PWM + (1−s)·background** (renormalized).  
3. Score sequences with **PWM log-odds**; plot **latent path** and mean score vs interpolation **t**.

## Key outputs

![Motif composition]({{ '/demos/scientific-generative-sequences/outputs/motif_composition.png' | relative_url }})

![Score distributions]({{ '/demos/scientific-generative-sequences/outputs/score_histograms.png' | relative_url }})

![Latent interpolation]({{ '/demos/scientific-generative-sequences/outputs/latent_interpolation.png' | relative_url }})

## Reproduce

{% include demo-source.html slug="scientific-generative-sequences" %}

```bash
cd demos/scientific-generative-sequences
python3 data/generate.py
python3 src/run.py
```

Dependencies: `demos/requirements.txt`.
