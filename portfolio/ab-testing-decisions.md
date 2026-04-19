---
layout: default
title: A/B testing decisions
description: Synthetic experiment data with effect size, confidence interval, and a decision summary.
banner_logo_right: true
---

## Business question

Did the change improve our primary metric, or could the difference plausibly be noise?

## What we would decide with this

Compare the **difference in means** to its **95% confidence interval**. If the interval excludes zero in the direction we care about, we have evidence to **ship** or **iterate**; otherwise **keep testing** or **stop** per your risk tolerance.

## Synthetic data

Independent samples for control and treatment, generated with different means and shared noise. **Seed: 42**. See `demos/ab-testing-decisions/data/generate.py`.

## Approach

Welch’s **t-test** (unequal variance) plus a **95% CI** for the mean difference (`scipy.stats`).

## Key outputs

![Control vs treatment distribution and summary]({{ '/demos/ab-testing-decisions/outputs/ab_summary.png' | relative_url }})

## Reproduce

{% include demo-source.html slug="ab-testing-decisions" %}

```bash
cd demos/ab-testing-decisions
python3 data/generate.py
python3 src/run.py
```

Dependencies: `demos/requirements.txt`.
