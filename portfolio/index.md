---
layout: default
title: Portfolio
description: Synthetic-data examples that mirror common business questions—forecasting, experiments, segmentation, and more.
banner_logo_right: true
---

Small, reproducible **Python** demos (synthetic data) illustrating how scientific and data workflows support decisions. Each example links to source under `demos/` in the [GitHub repository](https://github.com/BKAmos/BKAmos.github.io). Automated workflows for building and deploying this site live under the **Actions** tab on that repository.

<div class="home-industries" markdown="0">
<section class="home-industry">
<h2 class="home-industry-title"><a href="{% link portfolio/forecasting-uncertainty.md %}">Demand and uncertainty</a></h2>
<p>Forecast monthly demand with prediction intervals to frame inventory risk.</p>
</section>
<section class="home-industry">
<h2 class="home-industry-title"><a href="{% link portfolio/ab-testing-decisions.md %}">A/B testing decisions</a></h2>
<p>Turn experiment results into effect sizes, confidence intervals, and a plain-language decision.</p>
</section>
<section class="home-industry">
<h2 class="home-industry-title"><a href="{% link portfolio/segmentation-explainable.md %}">Segmentation</a></h2>
<p>Cluster customers or products and summarize each segment with interpretable profiles.</p>
</section>
<section class="home-industry">
<h2 class="home-industry-title"><a href="{% link portfolio/margin-whatif.md %}">Margin what-if</a></h2>
<p>Explore price and cost sensitivity with simple elasticity-style scenarios.</p>
</section>
<section class="home-industry">
<h2 class="home-industry-title"><a href="{% link portfolio/multimodal-support-signals.md %}">Multimodal support signals</a></h2>
<p>Fuse text, product/channel, and attachment signals; cluster and track weekly mix.</p>
</section>
<section class="home-industry">
<h2 class="home-industry-title"><a href="{% link portfolio/repeatable-weekly-report.md %}">Repeatable weekly report</a></h2>
<p>Generate a templated HTML report from CSVs with Python and Jinja2.</p>
</section>
</div>

<p class="portfolio-meta">All demos share dependencies listed in <code>demos/requirements.txt</code>. Run instructions are in <code>demos/README.md</code> and each demo folder.</p>

## Navigation

<p class="home-page-nav">
  <a href="{{ '/' | relative_url }}" class="btn">Home</a>
  <a href="{% link about.md %}" class="btn">About</a>
  <a href="{% link services.md %}" class="btn">Services</a>
  <a href="{% link portfolio/index.md %}" class="btn">Portfolio</a>
  <a href="{% link contact.md %}" class="btn">Contact</a>
</p>
