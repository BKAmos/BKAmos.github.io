---
layout: default
title: Agent-accessible DESeq workflow
description: Agent-orchestrated synthetic DESeq workflow with browser, REST, and MCP access surfaces. Published demo uses static sample outputs; clone locally for live runs.
banner_logo_right: true
---

<link rel="stylesheet" href="{{ '/assets/css/deseq-workflow-ui.css' | relative_url }}">

## Business question

Can an **orchestrator agent** delegate a reproducible **DESeq differential-expression workflow** to specialized tools and workers—while humans use the same pipeline through a web UI or REST/CLI?

## Agent orchestration pattern

This demo shows how one bioinformatics pipeline stays consistent across three surfaces:

- **Orchestrator agent** calls MCP tools (`run_deseq`, `get_job_status`, `get_deseq_results_summary`) through a Cloudflare Worker gateway.
- **Control plane API** validates synthetic-only requests, tracks job state, and serves artifact metadata.
- **Compute workers** run PyDESeq2 (Docker locally; optional AWS Lambda in advanced deployments).

A planner agent can submit work, poll status, and summarize results without re-implementing DESeq logic—the same contract the browser UI and CLI use.

## Try the workflow

Use the interactive panel below to inspect a **completed synthetic DESeq run** (volcano plot, results CSV, top genes). On the published site this loads committed sample outputs—no backend or API token required.

To submit **new** runs and exercise the full orchestration loop (UX + CLI + MCP agent tools), clone the repo and start the local stack with `start-demo` / `verify-demo`.

### Run this demo on your workstation

- [Quickstart and setup](https://github.com/BKAmos/BKAmos.github.io/blob/main/demos/agent-accessible-workflows/README.md)
- [Local validation runbook (queue + concurrency + MCP)](https://github.com/BKAmos/BKAmos.github.io/blob/main/demos/agent-accessible-workflows/runbook-local.md)
- [Demo folder contents](https://github.com/BKAmos/BKAmos.github.io/tree/main/demos/agent-accessible-workflows)

<script>
  window.DESEQ_WORKFLOW_CONFIG = {
    apiBaseUrl: {% if jekyll.environment == "development" %}"http://localhost:8000"{% else %}""{% endif %},
    demoMode: {% if jekyll.environment == "development" %}false{% else %}true{% endif %},
    sampleArtifactsBase: "{{ '/demos/agent-accessible-workflows/outputs' | relative_url }}"
  };
</script>

<div id="deseq-app" class="deseq-app">
  <section class="deseq-panel deseq-demo-note" id="demo-mode-note">
    <h2>Published demo mode</h2>
    <p>
      This page ships with a completed synthetic DESeq run so the workflow and artifacts are visible without a backend.
      Click <strong>Show sample DESeq run</strong> to replay the sample job flow, or clone the repo and use
      <code>start-demo</code> / <code>verify-demo</code> to submit new runs and connect MCP agent tools locally.
    </p>
  </section>

  <section class="deseq-panel">
    <h2>1. Analysis configuration</h2>
    <div class="deseq-grid">
      <label>Synthetic workload size
        <select id="synthetic-profile">
          <option value="serverless" selected>Serverless sample (100 genes x 8 samples)</option>
          <option value="small">Small (1,000 genes x 12 samples)</option>
          <option value="medium">Medium (5,000 genes x 24 samples)</option>
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
    <p class="portfolio-meta" style="margin-top: 0.75rem;">Synthetic-only RNA-seq jobs. No user-uploaded files in UX, CLI/API, or agent tools.</p>
  </section>

  <section class="deseq-panel">
    <h2>2. Submit and monitor</h2>
    <div class="deseq-actions">
      <button type="button" class="btn" id="run-synthetic">Run synthetic data through API</button>
    </div>
    <div id="deseq-status" class="deseq-status" data-kind="info">Loading published sample...</div>
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

Local runs support bounded synthetic presets (`small`, `medium`, `large`, plus a trimmed `serverless` profile). The published sample uses the serverless-sized matrix (100 genes × 8 samples, `~condition` design).

## Architecture

```text
Orchestrator agent → MCP gateway (Cloudflare Worker)
                  → REST API (FastAPI control plane)
                  → job queue (Redis, optional locally)
                  → PyDESeq2 worker containers
                  → per-job artifacts (CSV, plots, manifest)
```

| Surface | Role |
|---------|------|
| **Agent / MCP** | Orchestrator delegates `run_deseq`, polls `get_job_status`, summarizes with `get_deseq_results_summary` |
| **Browser UI** | Same job contract for guided submission and artifact preview |
| **CLI / REST** | Scripted batch submissions and automation |

Flow summary: `Agent / UX / CLI → API → queue (optional) → worker → artifacts → API responses`

## Optional REST example

```bash
curl -X POST "$API_BASE_URL/tools/run_deseq" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  --data-binary @fixtures/run-deseq-synthetic.json
```

## Agent tools

The Cloudflare Worker exposes MCP tools: `run_deseq`, `get_job_status`, `get_deseq_results_summary`, and `get_synthetic_dataset_info`. An orchestrator can plan analysis steps, submit synthetic jobs, poll to completion, and read structured summaries—without embedding PyDESeq2 in the agent itself.

## Optional AWS deployment

For experiments on a preview branch only, see [`src/aws-serverless/README.md`](https://github.com/BKAmos/BKAmos.github.io/blob/main/demos/agent-accessible-workflows/src/aws-serverless/README.md). Production portfolio pages do **not** use live AWS compute.

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

<script src="{{ '/assets/js/deseq-workflow-ui.js?v=20260526-static-demo' | relative_url }}"></script>
