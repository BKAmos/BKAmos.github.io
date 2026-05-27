---
layout: default
title: RNA-seq trust-and-DE learning loop
description: Minimal agent-orchestrated component — contamination QC, DESeq, cycle report, and parent handoff — for the SciAna portfolio.
banner_logo_right: true
---

<link rel="stylesheet" href="{{ '/assets/css/learning-loop-ui.css' | relative_url }}">

## Business question

**Should we trust this differential expression table?**

Before interpreting RNA-seq results, a team needs to know whether samples pass contamination QC and whether DE calls are stable under reasonable parameter changes. This page belongs to the **Agentic Orchestration** track: it composes standalone agentic components into a small learning loop that reports upward to a larger orchestrator (not built here).

## What this component does

Internal micro-loop (≤3 cycles):

1. **Contamination agent** — QC gate  
2. **DESeq agent** — expression under current parameters  
3. **Report agent** — cycle summary HTML + JSON  
4. **Local orchestrator** — reflect/adapt (`strictness`, `min_count`, profiles) and emit `component_summary.json`

**Stability check:** Jaccard overlap on top-10 genes between consecutive internal cycles (threshold 0.5).

### Run locally

- [Component README](https://github.com/BKAmos/BKAmos.github.io/blob/main/demos/agent-learning-orchestrator/README.md)
- [Local runbook](https://github.com/BKAmos/BKAmos.github.io/blob/main/demos/agent-learning-orchestrator/runbook-local.md)
- Sub-agents: [DESeq]({% link portfolio/agent-accessible-workflows.md %}), [Contamination]({% link portfolio/agent-contaminant-investigation.md %}), [Cycle report]({% link portfolio/repeatable-weekly-report.md %})
- [Agentic Orchestration track]({% link portfolio/agentic-orchestration.md %})

<script>
  window.LEARNING_LOOP_CONFIG = {
    apiBaseUrl: {% if jekyll.environment == "development" %}"http://localhost:8003"{% else %}""{% endif %},
    demoMode: {% if jekyll.environment == "development" %}false{% else %}true{% endif %},
    sampleSummaryBase: "{{ '/demos/agent-learning-orchestrator/outputs/component_summary.json' | relative_url }}"
  };
</script>

<div id="learning-loop-app" class="learning-loop-app">
  <section class="learning-loop-callout" id="learning-loop-demo-note">
    <strong>Component scope.</strong> This is one micro-loop in a composable agent architecture. A parent orchestrator would consume <code>component_summary.json</code> and route to downstream components (pathway analysis, multimodal validation, etc.).
  </section>

  <section class="learning-loop-panel">
    <h2>1. Configure component run</h2>
    <div class="learning-loop-grid">
      <label>Max internal cycles
        <input id="max-cycles" type="number" min="1" max="3" value="3">
      </label>
      <label>Contamination profile
        <select id="contam-profile">
          <option value="clean">Clean</option>
          <option value="low_contam" selected>Low contamination</option>
          <option value="high_contam">High contamination</option>
          <option value="edge_case">Edge case</option>
        </select>
      </label>
      <label>QC strictness
        <input id="contam-strictness" type="number" min="0.1" max="1.0" step="0.1" value="0.6">
      </label>
      <label>DESeq profile
        <select id="deseq-profile">
          <option value="small">Small</option>
          <option value="medium" selected>Medium</option>
          <option value="large">Large</option>
        </select>
      </label>
      <label>DESeq min count
        <input id="deseq-min-count" type="number" min="0" value="10">
      </label>
      <label>API token
        <input id="api-token" type="password" placeholder="Required when demo mode is off">
      </label>
    </div>
  </section>

  <section class="learning-loop-panel">
    <h2>2. Run micro-loop</h2>
    <div class="learning-loop-actions">
      <button type="button" class="btn" id="run-component">Run trust-and-DE component</button>
    </div>
    <div id="learning-loop-status" class="learning-loop-status">Ready.</div>
    <dl class="learning-loop-job">
      <dt>Component run ID</dt><dd id="component-run-id">not started</dd>
      <dt>Status</dt><dd id="component-status">idle</dd>
      <dt>Phase</dt><dd id="component-phase">idle</dd>
    </dl>
  </section>

  <section class="learning-loop-panel">
    <h2>3. Internal cycle timeline</h2>
    <ul id="cycle-timeline-list"></ul>
    <h3>Cycle comparison</h3>
    <div id="cycle-compare" class="learning-loop-compare"></div>
  </section>

  <section class="learning-loop-panel">
    <h2>4. Parent handoff</h2>
    <p class="learning-loop-handoff-action" id="handoff-action">pending</p>
    <p class="portfolio-meta" id="handoff-meta"></p>
    <p><strong>Blocking issues:</strong> <span id="handoff-blocking">None</span></p>
    <p><strong>Suggested next components (hints for parent):</strong></p>
    <ul id="handoff-next-components"></ul>
    <h3>component_summary.json</h3>
    <pre id="handoff-json" class="learning-loop-pre">{}</pre>
  </section>

  <section class="learning-loop-panel">
    <h2>Sub-agents in this component</h2>
    <ul id="sub-agent-links">
      <li><a href="{% link portfolio/agent-contaminant-investigation.md %}">Contamination investigation</a></li>
      <li><a href="{% link portfolio/agent-accessible-workflows.md %}">DESeq workflow</a></li>
      <li><a href="{% link portfolio/repeatable-weekly-report.md %}">Cycle report agent</a></li>
    </ul>
  </section>
</div>

<script src="{{ '/assets/js/learning-loop-ui.js' | relative_url }}" defer></script>
