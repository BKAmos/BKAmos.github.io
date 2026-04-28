---
layout: default
title: Agent-accessible DESeq workflow
description: Upload RNA-seq counts, run PyDESeq2 through a cloud job API, and expose the same workflow to power users and MCP agents.
banner_logo_right: true
---

<link rel="stylesheet" href="{{ '/assets/css/deseq-workflow-ui.css' | relative_url }}">

## Business question

Can a small lab or bioinformatics team run a reproducible **DESeq differential-expression workflow** through a web UI while giving power users and AI agents the same backend through REST and MCP?

## What we would decide with this

Use a lightweight UI for routine analysis, a documented API for automation, and an MCP gateway for agent workflows. The heavy computation stays in a Dockerized Python worker—on cloud compute in production, or on your machine via the same Compose stack used in the Oracle reference deployment.

## Try the workflow

This portfolio page includes a functional UI shell. In demo mode it previews the bundled synthetic outputs. When you run `bundle exec jekyll serve`, Jekyll uses development mode: the UI targets `http://localhost:8000` (run Docker Compose from `demos/agent-accessible-workflows/src` and use the same `API_TOKEN` as in `.env`). Production builds keep demo mode until you point a deployed API or Worker at this page.

<script>
  window.DESEQ_WORKFLOW_CONFIG = {
    apiBaseUrl: {% if jekyll.environment == "development" %}"http://localhost:8000"{% else %}""{% endif %},
    syntheticCountsUrl: "{{ '/demos/agent-accessible-workflows/data/counts.csv' | relative_url }}",
    syntheticMetadataUrl: "{{ '/demos/agent-accessible-workflows/data/metadata.csv' | relative_url }}",
    sampleManifestUrl: "{{ '/demos/agent-accessible-workflows/outputs/manifest.json' | relative_url }}",
    outputBaseUrl: "{{ '/demos/agent-accessible-workflows/outputs/' | relative_url }}",
    demoMode: {% if jekyll.environment == "development" %}false{% else %}true{% endif %}
  };
</script>

<div id="deseq-app" class="deseq-app">
  <section class="deseq-panel">
    <h2>1. Dataset</h2>
    <p>Use the bundled synthetic toy RNA-seq dataset, or upload a count matrix and sample metadata after the backend is deployed.</p>
    <p class="deseq-warning">Do not upload sensitive or regulated data to a public demo deployment. Real data should require authentication, private object storage, retention policies, and compliance review.</p>
    <div class="deseq-actions">
      <a class="btn" href="{{ '/demos/agent-accessible-workflows/data/counts.csv' | relative_url }}">Download counts.csv</a>
      <a class="btn" href="{{ '/demos/agent-accessible-workflows/data/metadata.csv' | relative_url }}">Download metadata.csv</a>
      <button type="button" class="btn" id="use-synthetic">Use synthetic toy dataset</button>
    </div>
    <label>Counts CSV <input type="file" id="counts-file" accept=".csv,text/csv"></label>
    <label>Metadata CSV <input type="file" id="metadata-file" accept=".csv,text/csv"></label>
    <p id="sample-summary" class="portfolio-meta"></p>
  </section>

  <section class="deseq-panel">
    <h2>2. Analysis configuration</h2>
    <div class="deseq-grid">
      <label>Condition column <input id="condition-column" value="condition"></label>
      <label>Reference level <input id="reference-level" value="control"></label>
      <label>Treatment level <input id="treatment-level" value="treated"></label>
      <label>Batch column <input id="batch-column" value="batch"></label>
      <label>Minimum count filter <input id="min-count" type="number" min="0" value="10"></label>
      <label>API token <input id="api-token" type="password" placeholder="Required for live jobs"></label>
    </div>
  </section>

  <section class="deseq-panel">
    <h2>3. Submit and monitor</h2>
    <div class="deseq-actions">
      <button type="button" class="btn" id="run-uploaded">Run uploaded data</button>
      <button type="button" class="btn" id="run-synthetic">Run synthetic data through API</button>
    </div>
    <div id="deseq-status" class="deseq-status" data-kind="info">Demo mode is active until a backend API URL is configured.</div>
    <dl class="deseq-job">
      <dt>Job ID</dt><dd id="job-id">sample-job</dd>
      <dt>Status</dt><dd id="job-state">sample outputs loaded</dd>
      <dt>Message</dt><dd id="job-message">Precomputed PyDESeq2 outputs are embedded below.</dd>
    </dl>
  </section>

  <section class="deseq-panel">
    <h2>4. Results preview</h2>
    <div class="deseq-actions" id="artifact-links">
      <a class="btn" href="{{ '/demos/agent-accessible-workflows/outputs/results.csv' | relative_url }}">results.csv</a>
      <a class="btn" href="{{ '/demos/agent-accessible-workflows/outputs/top_genes.csv' | relative_url }}">top_genes.csv</a>
      <a class="btn" href="{{ '/demos/agent-accessible-workflows/outputs/report.html' | relative_url }}">HTML report</a>
    </div>
    <div class="deseq-output-grid">
      <figure><img src="{{ '/demos/agent-accessible-workflows/outputs/volcano.png' | relative_url }}" alt="Volcano plot"><figcaption>Volcano plot</figcaption></figure>
      <figure><img src="{{ '/demos/agent-accessible-workflows/outputs/ma.png' | relative_url }}" alt="MA plot"><figcaption>MA plot</figcaption></figure>
      <figure><img src="{{ '/demos/agent-accessible-workflows/outputs/pca.png' | relative_url }}" alt="PCA plot"><figcaption>PCA plot</figcaption></figure>
      <figure><img src="{{ '/demos/agent-accessible-workflows/outputs/top_genes_heatmap.png' | relative_url }}" alt="Top genes heatmap"><figcaption>Top genes heatmap</figcaption></figure>
    </div>
    <h3>Top genes</h3>
    <div id="top-genes-table"></div>
  </section>
</div>

## Synthetic data

The toy set contains 12 samples, 1,000 genes, two conditions (`control` and `treated`), and a batch label. It is generated with a negative-binomial-like Gamma-Poisson process and a seeded subset of truly differential genes. See `demos/agent-accessible-workflows/data/generate.py`.

## Architecture

![Architecture: Cloudflare Worker gateway, FastAPI API, Redis queue, PyDESeq2 worker, object storage]({{ '/demos/agent-accessible-workflows/outputs/architecture.png' | relative_url }})

## Power-user REST example

```bash
curl -X POST "$API_BASE_URL/tools/run_deseq" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "synthetic",
    "condition_column": "condition",
    "reference_level": "control",
    "treatment_level": "treated",
    "batch_column": "batch",
    "min_count": 10
  }'
```

## Agent tools

The Cloudflare Worker exposes an MCP endpoint with tools for `run_deseq`, `get_job_status`, `get_deseq_results_summary`, and `get_synthetic_dataset_info`.

## Reproduce locally

{% include demo-source.html slug="agent-accessible-workflows" %}

```bash
cd demos/agent-accessible-workflows
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 data/generate.py
python3 src/run.py
```

<script src="{{ '/assets/js/deseq-workflow-ui.js' | relative_url }}"></script>
