---
layout: default
title: Agentic Orchestration
description: Multi-agent workflow orchestration examples that coordinate synthetic bioinformatics components and emit parent handoff artifacts.
banner_logo_right: true
---

Agentic orchestration demos focus on **coordination across components** rather than a single tool surface. These examples show how local agents can delegate work, reflect on intermediate results, adapt parameters, and produce a structured handoff for a parent workflow.

<div class="home-industries" markdown="0">
<section class="home-industry">
<h2 class="home-industry-title"><a href="{% link portfolio/agent-learning-orchestrator.md %}">RNA-seq trust-and-DE learning loop</a></h2>
<p>Coordinates contamination QC, DESeq differential expression, and cycle reporting over a shared synthetic study bundle, then emits <code>component_summary.json</code> for parent orchestration.</p>
</section>
</div>

<p class="portfolio-meta">Standalone agent-accessible components remain in the <a href="{% link portfolio/agent-accessible-workflows.md %}">Agentic DESeq workflow</a>, <a href="{% link portfolio/agent-contaminant-investigation.md %}">contamination investigation</a>, and <a href="{% link portfolio/repeatable-weekly-report.md %}">cycle report</a> pages.</p>

## Navigation

<p class="home-page-nav">
  <a href="{{ '/' | relative_url }}" class="btn">Home</a>
  <a href="{% link portfolio/index.md %}" class="btn">Portfolio overview</a>
  <a href="{% link portfolio/agent-accessible-workflows.md %}" class="btn">Agentic DESeq</a>
  <a href="{% link about.md %}" class="btn">About</a>
  <a href="{% link services.md %}" class="btn">Services</a>
  <a href="{% link contact.md %}" class="btn">Contact</a>
</p>
