---
layout: default
title: Agent-accessible DESeq workflow
description: Currently a work in progress. Assembing backend resources. You can download and run the mvp architecture on your local machine.
banner_logo_right: true
---

<link rel="stylesheet" href="{{ '/assets/css/deseq-workflow-ui.css' | relative_url }}">

## Business question

Can a small lab or bioinformatics team run a reproducible **DESeq differential-expression workflow** through a web UI while giving power users and AI agents the same backend through REST, CLI payloads, and MCP?

## What we can do with this

This architecture affords users of the software (employees) multiple ways of accessing the differential expression workflow. For example, if a user wanted to run a differential expression analsysis using an agent, the web page upload, or the command line, all three are viable.

## Try the workflow

This workflow demonstrates a practical pattern for analytics teams: one analysis pipeline, multiple access surfaces. A non-technical user can launch a synthetic DESeq run from the browser, a power user can automate the same run over REST/CLI, and an agent can orchestrate it through MCP tools. All three surfaces submit into the same backend job system, so results stay consistent while each audience gets the interface that fits how they work.

Its biggest strength is operational consistency under different usage styles. The queue-backed worker layer allows concurrent job execution, while the UI now renders run-specific artifacts only after the submitted job completes. That makes the demo useful both as a product UX prototype and as a systems proof-of-concept for reproducible, agent-accessible bioinformatics workflows.

To build this on your own desktop, start the local stack from `demos/agent-accessible-workflows` using the included quickstart scripts (`start-demo` and `verify-demo`), then open this portfolio page locally and submit runs with your generated `API_TOKEN`. The same packaged flow supports UX, CLI, and agent validation on a single workstation.

### Run this demo on your workstation

For technical reviewers, this project includes a copy-paste local package that runs UX + CLI + agent surfaces on one machine.

- [Quickstart and setup](https://github.com/BKAmos/BKAmos.github.io/blob/main/demos/agent-accessible-workflows/README.md)
- [Local validation runbook (queue + concurrency)](https://github.com/BKAmos/BKAmos.github.io/blob/main/demos/agent-accessible-workflows/runbook-local.md)
- [Demo folder contents](https://github.com/BKAmos/BKAmos.github.io/tree/main/demos/agent-accessible-workflows)

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
    <h2>1. Analysis configuration</h2>
    <div class="deseq-grid">
      <label>Synthetic workload size
        <select id="synthetic-profile">
          <option value="small">Small (1,000 genes x 12 samples)</option>
          <option value="medium" selected>Medium (5,000 genes x 24 samples)</option>
          <option value="large">Large (10,000 genes x 32 samples)</option>
        </select>
      </label>
      <label>Condition column <input id="condition-column" value="condition"></label>
      <label>Reference level <input id="reference-level" value="control"></label>
      <label>Treatment level <input id="treatment-level" value="treated"></label>
      <label>Batch column <input id="batch-column" value="batch"></label>
      <label>Minimum count filter <input id="min-count" type="number" min="0" value="10"></label>
      <label>API token <input id="api-token" type="password" placeholder="Required for live jobs"></label>
    </div>
    <p class="portfolio-meta" style="margin-top: 0.75rem;">This demo runs synthetic-only RNA-seq jobs. No user-uploaded files are accepted in UX, CLI/API, or agent tools.</p>
  </section>

  <section class="deseq-panel">
    <h2>2. Submit and monitor</h2>
    <div class="deseq-actions">
      <button type="button" class="btn" id="run-synthetic">Run synthetic data through API</button>
    </div>
    <div id="deseq-status" class="deseq-status" data-kind="info">Demo mode is active until a backend API URL is configured.</div>
    <dl class="deseq-job">
      <dt>Job ID</dt><dd id="job-id">not submitted</dd>
      <dt>Status</dt><dd id="job-state">idle</dd>
      <dt>Message</dt><dd id="job-message">Submit a job to render outputs for that run.</dd>
    </dl>
  </section>

  <section class="deseq-panel">
    <h2>3. Results preview (job-specific)</h2>
    <p id="results-placeholder" class="portfolio-meta">Artifacts and plots appear only after the submitted job completes.</p>
    <div class="deseq-actions is-hidden" id="artifact-links">
      <a class="btn" id="artifact-results" href="#" target="_blank" rel="noopener">results.csv</a>
      <a class="btn" id="artifact-top-genes" href="#" target="_blank" rel="noopener">top_genes.csv</a>
      <a class="btn" id="artifact-report" href="#" target="_blank" rel="noopener">HTML report</a>
    </div>
    <div id="live-image-grid" class="deseq-output-grid is-hidden"></div>
    <h3>Result CSV preview</h3>
    <pre id="result-csv-preview" class="deseq-code is-hidden" style="max-height: 14rem; overflow: auto; margin-top: 0.75rem; white-space: pre-wrap"></pre>
    <p id="result-csv-empty" class="portfolio-meta">No run-specific CSV preview yet.</p>
    <h3>All run artifacts</h3>
    <div class="deseq-actions">
      <ul id="live-artifacts"></ul>
    </div>
    <h3>Top genes</h3>
    <div id="top-genes-table" class="deseq-top-genes">
      <table>
        <thead>
          <tr><th>gene_id</th><th>log2FoldChange</th><th>padj</th><th>baseMean</th></tr>
        </thead>
        <tbody id="top-genes-body"></tbody>
      </table>
    </div>
  </section>
</div>

## Synthetic data

The live run flow supports bounded synthetic compute presets:
- `small`: 1,000 genes x 12 samples
- `medium`: 5,000 genes x 24 samples
- `large`: 10,000 genes x 32 samples

## Architecture

![Architecture: Cloudflare Worker gateway, FastAPI API, Redis queue, PyDESeq2 worker, object storage]({{ '/demos/agent-accessible-workflows/outputs/architecture.png' | relative_url }})

## Power-user REST example

```bash
curl -X POST "$API_BASE_URL/tools/run_deseq" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "synthetic",
    "synthetic_profile": "medium",
    "condition_column": "condition",
    "reference_level": "control",
    "treatment_level": "treated",
    "batch_column": "batch",
    "min_count": 10
  }'
```

## Agent tools

The Cloudflare Worker exposes an MCP endpoint with tools for `run_deseq`, `get_job_status`, `get_deseq_results_summary`, and `get_synthetic_dataset_info`. `run_deseq` remains available to agents with synthetic-only inputs and profile selection.

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
