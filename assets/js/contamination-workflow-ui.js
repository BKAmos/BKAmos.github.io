(function () {
  "use strict";

  const cfg = window.CONTAMINATION_WORKFLOW_CONFIG || {};
  const onLoopback = /^localhost$/i.test(window.location.hostname) || window.location.hostname === "127.0.0.1";
  if (onLoopback && !cfg.apiBaseUrl) cfg.apiBaseUrl = "http://localhost:8000";
  const sampleArtifactsBase = cfg.sampleArtifactsBase || "/demos/agent-contaminant-investigation/outputs";
  const SAMPLE_JOB = {
    job_id: "sample-job",
    status: "completed",
    summary: {
      executive_summary: "Investigation found elevated non-host reads and marker evidence consistent with possible foreign genetic material.",
      confidence: 0.711,
    },
    signals: [
      { name: "max_non_host_ratio", value: 0.02325 },
      { name: "max_marker_hits", value: 7 },
      { name: "max_negative_control_contaminant_reads", value: 5 },
      { name: "risk_score", value: 71.069 },
    ],
    verdict: {
      verdict: "contaminant_likely",
      confidence: 0.711,
      requires_reiteration: false,
      recommended_next_steps: [
        "Re-sequence highest-risk samples with deeper host depletion.",
        "Inspect negative controls for prep contamination trends.",
        "Validate top contaminant taxa via orthogonal assay (qPCR).",
      ],
    },
    timeline: [
      { stage: "overview", status: "ok" },
      { stage: "investigator", status: "ok" },
      { stage: "executor", status: "ok" },
      { stage: "summary", status: "ok" },
      { stage: "verdict", status: "ok" },
    ],
    artifacts: [
      "overview.json",
      "investigator_plan.json",
      "evidence.json",
      "summary.json",
      "verdict.json",
      "timeline.json",
      "top_non_host_taxa.png",
      "report.html",
    ],
  };

  function $(sel) {
    return document.querySelector(sel);
  }

  function setStatus(message) {
    const el = $("#contam-status");
    if (el) el.textContent = message;
  }

  function authHeaders() {
    const token = $("#api-token")?.value?.trim();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  function authTokenValue() {
    return $("#api-token")?.value?.trim() || "";
  }

  function isDemoMode() {
    return cfg.demoMode === true || !cfg.apiBaseUrl;
  }

  function stageLabel(stage) {
    return String(stage || "unknown").replace(/_/g, " ");
  }

  function sampleArtifactHref(name) {
    return `${sampleArtifactsBase.replace(/\/$/, "")}/${encodeURIComponent(name)}`;
  }

  function artifactHref(artifact, jobId, name, sampleMode) {
    if (sampleMode) return sampleArtifactHref(name);

    const fallbackPath = `/jobs/${jobId}/artifacts/${encodeURIComponent(name)}`;
    const rawUrl = typeof artifact === "string" ? fallbackPath : (artifact.url || fallbackPath);
    const href = /^https?:\/\//i.test(rawUrl)
      ? new URL(rawUrl)
      : new URL(rawUrl.startsWith("/") ? rawUrl : `/${rawUrl}`, cfg.apiBaseUrl);
    const token = authTokenValue();
    if (token) href.searchParams.set("token", token);
    return href.toString();
  }

  function renderTimeline(job) {
    const timeline = $("#timeline-list");
    if (!timeline) return;
    timeline.innerHTML = "";

    const stages = Array.isArray(job.timeline) ? job.timeline : [];
    if (stages.length === 0) {
      const li = document.createElement("li");
      li.textContent = "Timeline will appear after the backend reports progress.";
      timeline.appendChild(li);
      return;
    }

    stages.forEach((entry) => {
      const li = document.createElement("li");
      const status = entry?.status ? `: ${entry.status}` : "";
      li.textContent = `${stageLabel(entry?.stage)}${status}`;
      timeline.appendChild(li);
    });
  }

  function renderArtifacts(job, sampleMode) {
    const artifactsEl = $("#artifact-list");
    if (!artifactsEl) return;
    artifactsEl.innerHTML = "";

    const artifacts = Array.isArray(job.artifacts) ? job.artifacts : [];
    if (artifacts.length === 0) {
      const li = document.createElement("li");
      li.textContent = "No artifacts returned for this run.";
      artifactsEl.appendChild(li);
      return;
    }

    artifacts.forEach((artifact) => {
      const name = typeof artifact === "string" ? artifact : artifact?.name;
      if (!name) return;

      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = artifactHref(artifact, job.job_id || job.id || "sample-job", name, sampleMode);
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = name;
      li.appendChild(a);
      artifactsEl.appendChild(li);

      if (name.toLowerCase().endsWith(".png")) {
        const img = document.createElement("img");
        img.src = a.href;
        img.alt = name;
        img.loading = "lazy";
        img.className = "contam-artifact-image";
        li.appendChild(img);
      }
    });
  }

  function renderSignals(job) {
    const signalBox = $("#signal-box");
    if (!signalBox) return;

    signalBox.textContent = JSON.stringify({
      executive_summary: job.summary?.executive_summary,
      signals: job.signals || job.summary?.signals || [],
      verdict: job.verdict?.verdict,
      confidence: job.verdict?.confidence || job.summary?.confidence,
      recommended_next_steps: job.verdict?.recommended_next_steps || [],
    }, null, 2);
  }

  function renderJob(job, options) {
    const sampleMode = Boolean(options?.sampleMode);
    $("#job-id").textContent = job.job_id || job.id || (sampleMode ? "sample-job" : "not submitted");
    $("#job-state").textContent = sampleMode ? "sample completed" : (job.status || "unknown");
    if (job.verdict && job.verdict.verdict) $("#job-verdict").textContent = job.verdict.verdict;

    renderTimeline(job);
    renderArtifacts(job, sampleMode);
    renderSignals(job);
  }

  function payload() {
    return {
      dataset: "synthetic",
      profile: $("#profile").value,
      sample_count: Number($("#sample-count").value || 24),
      strictness: Number($("#strictness").value || 0.6),
      max_iterations: Number($("#max-iterations").value || 2),
      synthetic_seed: Number($("#seed").value || 42),
    };
  }

  async function submit() {
    if (isDemoMode()) {
      renderJob(SAMPLE_JOB, { sampleMode: true });
      setStatus("Demo mode: showing a completed synthetic sample run. Start the local backend to submit new payloads.");
      return;
    }
    setStatus("Submitting investigation...");
    const res = await fetch(`${cfg.apiBaseUrl}/tools/run_investigation`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(payload()),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    $("#job-id").textContent = data.job_id;
    $("#artifact-list").innerHTML = "";
    $("#timeline-list").innerHTML = "";
    poll(data.job_id);
  }

  async function poll(jobId) {
    try {
      const res = await fetch(`${cfg.apiBaseUrl}/jobs/${jobId}`, { headers: authHeaders() });
      if (!res.ok) throw new Error(await res.text());
      const job = await res.json();
      $("#job-state").textContent = job.status || "unknown";
      if (job.verdict && job.verdict.verdict) $("#job-verdict").textContent = job.verdict.verdict;
      if (job.status === "completed") {
        setStatus("Completed.");
        renderJob({ ...job, job_id: jobId }, { sampleMode: false });
        return;
      }
      if (job.status === "failed") {
        setStatus(job.message || "Run failed");
        return;
      }
      setStatus(`Polling (${job.status || "running"})...`);
      setTimeout(() => poll(jobId), 2500);
    } catch (err) {
      setStatus(`Polling failed: ${err && err.message ? err.message : String(err)}`);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    const demoMode = isDemoMode();
    const demoNote = $("#demo-mode-note");
    if (demoNote) demoNote.hidden = !demoMode;
    if (demoMode) {
      const runButton = $("#run-investigation");
      if (runButton) runButton.textContent = "Show sample investigation";
      renderJob(SAMPLE_JOB, { sampleMode: true });
      setStatus("Demo mode: sample run loaded. Start the local backend to run new configurations.");
    }

    $("#run-investigation")?.addEventListener("click", () => submit().catch((e) => setStatus(e.message)));
  });
})();
