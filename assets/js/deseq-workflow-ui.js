(function () {
  "use strict";

  const raw = window.DESEQ_WORKFLOW_CONFIG || {};
  const onLoopback =
    /^localhost$/i.test(window.location.hostname) ||
    window.location.hostname === "127.0.0.1" ||
    window.location.hostname === "[::1]";

  const config = Object.assign({}, raw);
  if (onLoopback) {
    if (!String(config.apiBaseUrl || "").trim()) {
      config.apiBaseUrl = "http://localhost:8000";
    }
    config.demoMode = false;
  } else {
    if (config.demoMode === "false") config.demoMode = false;
    if (config.demoMode === "true") config.demoMode = true;
  }

  const sampleArtifactsBase =
    config.sampleArtifactsBase || "/demos/agent-accessible-workflows/outputs";

  function isDemoMode() {
    return config.demoMode === true || !String(config.apiBaseUrl || "").trim();
  }

  function isAwsApi() {
    try {
      const host = new URL(config.apiBaseUrl).hostname;
      return host.includes("execute-api.") && host.endsWith(".amazonaws.com");
    } catch (_err) {
      return false;
    }
  }

  function liveSubmitEnabled() {
    return Boolean(String(config.apiBaseUrl || "").trim() && config.demoMode !== true);
  }

  function applyProfileConstraints() {
    const select = $("#synthetic-profile");
    if (!select) return;
    if (isAwsApi()) {
      select.value = "serverless";
      Array.from(select.options).forEach((opt) => {
        opt.disabled = opt.value !== "serverless";
      });
      $("#batch-column")?.setAttribute("disabled", "disabled");
    } else {
      Array.from(select.options).forEach((opt) => {
        opt.disabled = false;
      });
      $("#batch-column")?.removeAttribute("disabled");
    }
  }

  function applyDemoModeUi() {
    const tokenField = $("#api-token");
    const tokenLabel = tokenField?.closest("label");
    if (tokenLabel) tokenLabel.hidden = isDemoMode();
    if (isDemoMode()) {
      const runButton = $("#run-synthetic");
      if (runButton) runButton.textContent = "Show sample DESeq run";
    }
  }

  const state = {
    jobId: null,
    pollTimer: null,
    artifactsByName: {},
    sampleManifest: null,
  };

  function $(selector) {
    return document.querySelector(selector);
  }

  function setStatus(message, kind) {
    const box = $("#deseq-status");
    if (!box) return;
    box.textContent = message;
    box.dataset.kind = kind || "info";
  }

  function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function getFormValues() {
    return {
      synthetic_profile: $("#synthetic-profile")?.value || "medium",
      condition_column: $("#condition-column").value.trim() || "condition",
      reference_level: $("#reference-level").value.trim() || "control",
      treatment_level: $("#treatment-level").value.trim() || "treated",
      batch_column: $("#batch-column").value.trim() || null,
      min_count: Number($("#min-count").value || 10),
    };
  }

  function authHeaders() {
    const token = $("#api-token")?.value?.trim();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  function sampleArtifactHref(name) {
    return `${sampleArtifactsBase.replace(/\/$/, "")}/${encodeURIComponent(name)}`;
  }

  function artifactUrl(name) {
    return `${config.apiBaseUrl}/jobs/${state.jobId}/artifacts/${encodeURIComponent(name)}`;
  }

  function absoluteApiUrl(url) {
    try {
      return new URL(url, config.apiBaseUrl).href;
    } catch (_err) {
      return url;
    }
  }

  function hideLiveResults() {
    $("#results-placeholder")?.classList.remove("is-hidden");
    const list = $("#live-artifacts");
    if (list) list.innerHTML = "";
    clearArtifactPreview();
    state.artifactsByName = {};
  }

  function mapArtifacts(artifacts, options) {
    const sampleMode = Boolean(options?.sampleMode);
    const mapped = artifacts.map((artifact) => {
      const name = typeof artifact === "string" ? artifact : artifact.name;
      let url;
      let downloadUrl;
      if (sampleMode) {
        url = sampleArtifactHref(name);
        downloadUrl = url;
      } else {
        url = typeof artifact === "string" ? artifactUrl(name) : artifact.url || artifactUrl(name);
        downloadUrl =
          typeof artifact === "string"
            ? artifactUrl(name)
            : artifact.download_url || artifact.url || artifactUrl(name);
      }
      return {
        name,
        kind: typeof artifact === "string" ? "file" : artifact.kind || "file",
        contentType: typeof artifact === "string" ? "" : String(artifact.content_type || ""),
        url: sampleMode ? url : absoluteApiUrl(url),
        downloadUrl: sampleMode ? downloadUrl : absoluteApiUrl(downloadUrl),
      };
    });
    state.artifactsByName = mapped.reduce((acc, artifact) => {
      acc[artifact.name] = artifact;
      return acc;
    }, {});
    return mapped;
  }

  function shouldRenderArtifact(artifact, job) {
    if (job?.report_url && artifact.name === "report.html") return false;
    if (artifact.name === "pydeseq2.log") return false;
    return true;
  }

  function extensionFor(artifact) {
    return artifact.name.split("?")[0].split("#")[0].toLowerCase().split(".").pop() || "";
  }

  function isCsvArtifact(artifact) {
    return extensionFor(artifact) === "csv" || artifact.contentType.toLowerCase().startsWith("text/csv");
  }

  function isImageArtifact(artifact) {
    return /\.(png|jpe?g|gif|webp)$/i.test(artifact.name) || artifact.contentType.toLowerCase().startsWith("image/");
  }

  function clearArtifactPreview() {
    const preview = $("#artifact-preview");
    const body = $("#artifact-preview-body");
    if (preview) preview.classList.add("is-hidden");
    if (body) body.innerHTML = "";
  }

  function renderArtifactPreview(title, url, isImage) {
    const preview = $("#artifact-preview");
    const heading = $("#artifact-preview-title");
    const body = $("#artifact-preview-body");
    if (!preview || !heading || !body) return;

    body.innerHTML = "";
    heading.textContent = title;
    const element = document.createElement(isImage ? "img" : "iframe");
    element.src = url;
    element.title = title;
    if (isImage) {
      element.alt = title;
    } else {
      element.loading = "lazy";
    }
    body.appendChild(element);
    preview.classList.remove("is-hidden");
  }

  function createArtifactControl(artifact) {
    if (isCsvArtifact(artifact)) {
      const link = document.createElement("a");
      link.className = "btn";
      link.href = artifact.downloadUrl;
      link.download = artifact.name;
      link.textContent = artifact.name;
      return link;
    }

    const control = document.createElement(isImageArtifact(artifact) ? "button" : "a");
    control.className = "btn";
    control.textContent = artifact.name;
    if (isImageArtifact(artifact)) {
      control.type = "button";
      control.addEventListener("click", () => renderArtifactPreview(artifact.name, artifact.url, true));
    } else {
      control.href = artifact.url;
    }
    return control;
  }

  async function renderArtifacts(artifacts, job, options) {
    const sampleMode = Boolean(options?.sampleMode);
    const mapped = mapArtifacts(artifacts, { sampleMode });
    const list = $("#live-artifacts");
    if (!list) return;
    list.innerHTML = "";

    if (job?.report_url && !sampleMode) {
      const li = document.createElement("li");
      const button = document.createElement("button");
      const reportUrl = absoluteApiUrl(job.report_url);
      button.className = "btn";
      button.type = "button";
      button.addEventListener("click", () => renderArtifactPreview("Report", reportUrl, false));
      button.textContent = "Open report";
      li.appendChild(button);
      list.appendChild(li);
    }

    mapped
      .filter((artifact) => shouldRenderArtifact(artifact, job))
      .forEach((artifact) => {
        const li = document.createElement("li");
        li.appendChild(createArtifactControl(artifact));
        list.appendChild(li);
      });
    $("#results-placeholder")?.classList.add("is-hidden");
  }

  async function loadSampleManifest() {
    if (state.sampleManifest) return state.sampleManifest;
    const response = await fetch(`${sampleArtifactsBase.replace(/\/$/, "")}/manifest.json`);
    if (!response.ok) {
      throw new Error("Could not load the published sample manifest.");
    }
    state.sampleManifest = await response.json();
    return state.sampleManifest;
  }

  async function renderSampleJob(manifest, options) {
    const sampleMode = Boolean(options?.sampleMode);
    state.jobId = manifest.job_id || "portfolio-demo";
    $("#job-id").textContent = state.jobId;
    $("#job-state").textContent = sampleMode ? "sample completed" : manifest.status || "completed";
    $("#job-message").textContent = sampleMode
      ? "Published sample run from committed portfolio outputs."
      : "PyDESeq2 differential expression complete.";
    await renderArtifacts(manifest.artifacts || [], manifest, { sampleMode });
  }

  async function submitDemoJob() {
    hideLiveResults();
    setStatus("Submitting DESeq job (demo)...", "info");
    $("#job-id").textContent = "pending";
    $("#job-state").textContent = "submitting";
    $("#job-message").textContent = "Queueing synthetic job...";

    await delay(350);
    $("#job-state").textContent = "queued";
    $("#job-message").textContent = "Waiting for worker...";
    await delay(500);
    $("#job-state").textContent = "running";
    $("#job-message").textContent = "Running PyDESeq2 on synthetic counts...";
    await delay(650);

    const manifest = await loadSampleManifest();
    await renderSampleJob(manifest, { sampleMode: true });
    setStatus(
      "Demo mode: sample run complete. Clone the repo and use start-demo for live UX, CLI, and MCP runs.",
      "success",
    );
  }

  async function submitJob() {
    if (isDemoMode()) {
      await submitDemoJob();
      return;
    }

    const token = $("#api-token")?.value?.trim();
    if (!token) {
      setStatus("Paste the API token from demos/agent-accessible-workflows/src/.env (API_TOKEN=…) first.", "error");
      return;
    }

    setStatus("Submitting DESeq job...", "info");
    hideLiveResults();
    $("#job-state").textContent = "submitting";
    $("#job-message").textContent = "Submitting synthetic job to API...";
    const payload = {
      ...getFormValues(),
      dataset: "synthetic",
    };

    let response;
    try {
      response = await fetch(`${config.apiBaseUrl}/tools/run_deseq`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(),
        },
        body: JSON.stringify(payload),
      });
    } catch (err) {
      const msg = err && err.message ? err.message : String(err);
      if (isAwsApi()) {
        throw new Error(
          `${msg} — Could not reach the AWS API at ${config.apiBaseUrl}. Check the URL in _config.yml (deseq_api_url), CORS, and your network.`,
        );
      }
      throw new Error(
        `${msg} — Is Docker Compose up? Open http://localhost:8000/healthz in a browser.`,
      );
    }
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`HTTP ${response.status}: ${detail || response.statusText}`);
    }
    const data = await response.json();
    state.jobId = data.job_id;
    $("#job-id").textContent = state.jobId || "not submitted";
    setStatus(`Job ${state.jobId} submitted. Polling status...`, "success");
    pollJob();
  }

  async function pollJob() {
    if (!state.jobId) return;
    clearTimeout(state.pollTimer);
    try {
      const response = await fetch(`${config.apiBaseUrl}/jobs/${state.jobId}`, {
        headers: authHeaders(),
      });
      if (!response.ok) throw new Error(await response.text());
      const job = await response.json();
      $("#job-state").textContent = job.status || job.state || "unknown";
      $("#job-message").textContent = job.message || "";
      if (job.status === "completed" || job.state === "completed") {
        setStatus("Job complete. Results are ready below.", "success");
        await renderArtifacts(job.artifacts || [], job);
        return;
      }
      if (job.status === "failed" || job.state === "failed") {
        setStatus(job.error || "Job failed.", "error");
        return;
      }
      state.pollTimer = setTimeout(pollJob, 3000);
    } catch (error) {
      setStatus(error.message, "error");
    }
  }

  function bindEvents() {
    $("#run-synthetic")?.addEventListener("click", () =>
      submitJob().catch((error) => setStatus(error.message, "error")),
    );
    $("#poll-job")?.addEventListener("click", pollJob);
  }

  document.addEventListener("DOMContentLoaded", async () => {
    bindEvents();
    applyProfileConstraints();
    applyDemoModeUi();
    hideLiveResults();

    const demoNote = $("#demo-mode-note");
    if (demoNote) demoNote.hidden = !isDemoMode();

    if (isDemoMode()) {
      try {
        const manifest = await loadSampleManifest();
        await renderSampleJob(manifest, { sampleMode: true });
        setStatus(
          "Demo mode: published sample run loaded. Clone the repo and use start-demo for live UX, CLI, and MCP runs.",
          "info",
        );
      } catch (error) {
        setStatus(error.message, "error");
      }
      return;
    }

    if (isAwsApi()) {
      setStatus("Live AWS API: serverless profile only (100 genes, ~condition design).", "info");
    } else {
      setStatus("Ready. Submit a synthetic job to generate run-specific outputs.", "info");
    }
  });
})();
