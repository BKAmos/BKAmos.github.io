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
    <h3>Results</h3>
    <div class="deseq-actions">
      <ul id="live-artifacts"></ul>
    </div>
    <div id="artifact-preview" class="deseq-artifact-preview is-hidden" aria-live="polite">
      <h3 id="artifact-preview-title">Artifact preview</h3>
      <div id="artifact-preview-body"></div>
    </div>
  </section>
</div>

## Synthetic data

The live run flow supports bounded synthetic compute presets:
- `small`: 1,000 genes x 12 samples
- `medium`: 5,000 genes x 24 samples
- `large`: 10,000 genes x 32 samples

## Architecture

This workflow uses a single backend pipeline with multiple access surfaces:

- **UX surface:** portfolio web page for guided run submission
- **CLI/API surface:** direct REST calls and scripted batch submissions
- **Agent surface:** Cloudflare Worker MCP gateway (`run_deseq`, status, summary tools)
- **Control plane:** FastAPI endpoint handling auth, job submission, and artifact access
- **Queue layer:** Redis-backed queue for concurrent job orchestration
- **Compute layer:** Dockerized PyDESeq2 workers executing synthetic differential expression runs
- **Artifact layer:** per-job outputs (CSV + plots + report) returned through API artifact endpoints

Flow summary: `UX / CLI / Agent -> API -> Redis queue -> Worker containers -> job artifacts -> API responses/UI rendering`

## Optional REST example

```bash
curl -X POST "$API_BASE_URL/tools/run_deseq" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  --data-binary @fixtures/run-deseq-synthetic.json
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

<script src="{{ '/assets/js/deseq-workflow-ui.js?v=20260429-inline-preview' | relative_url }}"></script>
