---
layout: default
title: Agentic contamination investigation workflow
description: Local-first interactive demo for detecting likely foreign genetic material and contaminants using a guarded multi-agent investigation loop.
banner_logo_right: true
---

<link rel="stylesheet" href="{{ '/assets/css/contamination-workflow-ui.css' | relative_url }}">

## Run as component

This contamination agent is the QC gate in the [RNA-seq trust-and-DE learning loop]({% link portfolio/agent-learning-orchestrator.md %}). Run investigations standalone here, or invoke via the orchestrator as part of the trust-before-expression micro-loop.

## Question

Can a lab team triage likely foreign genetic material or contamination signals using one local workflow that supports browser UX, CLI, and agent tools?

## How this demo works

This demo mirrors an agentic investigation pattern:

`overview -> investigator plan -> guardrailed execution -> summary -> verdict`

All runs are synthetic-only and local-first. No external backend is required.

### Run locally

- [Demo README](https://github.com/BKAmos/BKAmos.github.io/blob/main/demos/agent-contaminant-investigation/README.md)
- [Local runbook](https://github.com/BKAmos/BKAmos.github.io/blob/main/demos/agent-contaminant-investigation/runbook-local.md)

<script>
  window.CONTAMINATION_WORKFLOW_CONFIG = {
    apiBaseUrl: {% if jekyll.environment == "development" %}"http://localhost:8000"{% else %}""{% endif %},
    demoMode: {% if jekyll.environment == "development" %}false{% else %}true{% endif %},
    sampleArtifactsBase: "{{ '/demos/agent-contaminant-investigation/outputs' | relative_url }}"
  };
</script>

<div id="contam-app" class="contam-app">
  <section class="contam-demo-note" id="demo-mode-note">
    <h2>Published demo mode</h2>
    <p>
      This page ships with a completed synthetic sample run so the investigation flow is visible without a local backend.
      To submit new runs, start the FastAPI service locally and open the site from Jekyll.
    </p>
  </section>

  <section class="contam-panel">
    <h2>1. Configure run</h2>
    <div class="contam-grid">
      <label>Profile
        <select id="profile">
          <option value="clean">Clean</option>
          <option value="low_contam" selected>Low contamination</option>
          <option value="high_contam">High contamination</option>
          <option value="edge_case">Edge case</option>
        </select>
      </label>
      <label>Samples <input id="sample-count" type="number" min="6" max="128" value="24"></label>
      <label>Strictness <input id="strictness" type="number" min="0.1" max="1.0" step="0.1" value="0.6"></label>
      <label>Iterations <input id="max-iterations" type="number" min="1" max="3" value="2"></label>
      <label>Seed <input id="seed" type="number" min="0" value="42"></label>
      <label>API token <input id="api-token" type="password" placeholder="Required when demo mode is off"></label>
    </div>
  </section>

  <section class="contam-panel">
    <h2>2. Submit</h2>
    <button type="button" class="btn" id="run-investigation">Run contamination investigation</button>
    <div id="contam-status" class="contam-status">Ready.</div>
    <dl class="contam-job">
      <dt>Job ID</dt><dd id="job-id">not submitted</dd>
      <dt>Status</dt><dd id="job-state">idle</dd>
      <dt>Verdict</dt><dd id="job-verdict">pending</dd>
    </dl>
  </section>

  <section class="contam-panel">
    <h2>3. Stage timeline</h2>
    <ul id="timeline-list"></ul>
    <h3>Key signals</h3>
    <pre id="signal-box" class="contam-pre">Signals appear after completion.</pre>
    <h3>Artifacts</h3>
    <ul id="artifact-list"></ul>
  </section>
</div>

<script src="{{ '/assets/js/contamination-workflow-ui.js?v=20260507' | relative_url }}"></script>
