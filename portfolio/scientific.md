---
layout: default
title: Scientific portfolio
description: Six synthetic biology-flavored demos spanning bioinformatics, cheminformatics, predictive biology, contacts, generative sequence models, and multimodal integration.
banner_logo_right: true
---

Reproducible **Python** demos using **synthetic data** shaped like biological and chemical experiments. Each piece links to code under `demos/` in the [GitHub repository](https://github.com/BKAmos/BKAmos.github.io). Figures are checked in under each demo’s `outputs/` folder.

<div class="home-industries" markdown="0">
<section class="home-industry">
<h2 class="home-industry-title"><a href="{% link portfolio/scientific-bioinformatics-de.md %}">Differential expression (toy)</a></h2>
<p>Gene-level summaries across two conditions; volcano plot with Benjamini–Hochberg FDR.</p>
</section>
<section class="home-industry">
<h2 class="home-industry-title"><a href="{% link portfolio/scientific-cheminformatics-similarity.md %}">Compound similarity (no RDKit)</a></h2>
<p>Synthetic fingerprints and physicochemical properties; Tanimoto similarity and PCA landscape.</p>
</section>
<section class="home-industry">
<h2 class="home-industry-title"><a href="{% link portfolio/scientific-predictive-dose-response.md %}">Dose–response / viability</a></h2>
<p>Hill-style synthetic curves; fitted potency and uncertainty for prediction-style readouts.</p>
</section>
<section class="home-industry">
<h2 class="home-industry-title"><a href="{% link portfolio/scientific-structural-contacts.md %}">Residue contact map</a></h2>
<p>Synthetic Cα distances; binary contact map at a distance threshold.</p>
</section>
<section class="home-industry">
<h2 class="home-industry-title"><a href="{% link portfolio/scientific-generative-sequences.md %}">Generative sequences (PWM + latent)</a></h2>
<p>Motif sampling with strength modulated by a 2D latent vector; scores and interpolation.</p>
</section>
<section class="home-industry">
<h2 class="home-industry-title"><a href="{% link portfolio/scientific-multimodal-biology.md %}">Multimodal biological samples</a></h2>
<p>Expression, imaging-style features, and clinical covariates; fused view with CCA.</p>
</section>
</div>

<p class="portfolio-meta">Dependencies: <code>demos/requirements.txt</code>. Run <code>python3 data/generate.py</code> then <code>python3 src/run.py</code> in each demo folder.</p>

## Navigation

<p class="home-page-nav">
  <a href="{{ '/' | relative_url }}" class="btn">Home</a>
  <a href="{% link portfolio/index.md %}" class="btn">Portfolio overview</a>
  <a href="{% link portfolio/business.md %}" class="btn">Business questions</a>
  <a href="{% link about.md %}" class="btn">About</a>
  <a href="{% link services.md %}" class="btn">Services</a>
  <a href="{% link contact.md %}" class="btn">Contact</a>
</p>
