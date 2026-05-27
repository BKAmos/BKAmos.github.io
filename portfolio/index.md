---
layout: default
title: Portfolio
description: Business, scientific, and agentic examples built as reproducible synthetic-data demos.
banner_logo_right: true
---

The portfolio is split into four tracks. **Business** mirrors common analytics decisions such as forecasting, experiments, segmentation, and reporting. **Scientific** showcases biology- and chemistry-flavored workflows built on synthetic data. **Agentic** contains single-workflow demos designed for multiple access surfaces, including UI, REST/CLI, and agent tooling. **Agentic Orchestration** contains multi-agent coordination examples that compose those surfaces into larger workflows.

<div class="home-industries" markdown="0">
<section class="home-industry">
<h2 class="home-industry-title"><a href="{% link portfolio/business.md %}">Business</a></h2>
<p>Six demos: demand and uncertainty, A/B testing, segmentation, margin what-if, multimodal support signals, and repeatable weekly reporting.</p>
</section>
<section class="home-industry">
<h2 class="home-industry-title"><a href="{% link portfolio/scientific.md %}">Scientific</a></h2>
<p>Six demos: differential expression, compound similarity, dose-response, contact maps, generative sequences, and multimodal biological integration.</p>
</section>
<section class="home-industry">
<h2 class="home-industry-title"><a href="{% link portfolio/agent-accessible-workflows.md %}">Agentic</a></h2>
<p>Single-workflow agent-accessible demos. The <a href="{% link portfolio/agent-accessible-workflows.md %}">DESeq workflow</a> demonstrates one synthetic bioinformatics pipeline exposed through browser UX, REST/CLI, and MCP-style agent tools.</p>
</section>
<section class="home-industry">
<h2 class="home-industry-title"><a href="{% link portfolio/agentic-orchestration.md %}">Agentic Orchestration</a></h2>
<p>Multi-agent coordination demos. The <a href="{% link portfolio/agent-learning-orchestrator.md %}">RNA-seq trust-and-DE learning loop</a> coordinates contamination QC, DESeq, and cycle reporting, then emits <code>component_summary.json</code> for parent handoff.</p>
</section>
</div>

<p class="portfolio-meta">Source for every demo lives under <code>demos/</code> in the <a href="https://github.com/BKAmos/BKAmos.github.io">GitHub repository</a>. Use the nested <strong>Portfolio</strong> menu above for direct links to each piece.</p>

## Navigation

<p class="home-page-nav">
  <a href="{{ '/' | relative_url }}" class="btn">Home</a>
  <a href="{% link about.md %}" class="btn">About</a>
  <a href="{% link services.md %}" class="btn">Services</a>
  <a href="{% link portfolio/index.md %}" class="btn">Portfolio</a>
  <a href="{% link contact.md %}" class="btn">Contact</a>
</p>
