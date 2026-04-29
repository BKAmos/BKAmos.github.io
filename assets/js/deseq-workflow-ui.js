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

  function liveSubmitEnabled() {
    return Boolean(String(config.apiBaseUrl || "").trim() && config.demoMode !== true);
  }

  const state = {
    jobId: null,
    pollTimer: null,
    artifactsByName: {},
    blobUrls: [],
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
    const token = $("#api-token").value.trim();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async function parseCsvPreview(url, maxRows, headers) {
    const response = await fetch(url, headers ? { headers } : undefined);
    if (!response.ok) throw new Error(`Could not fetch ${url}`);
    const text = await response.text();
    return text.split(/\r?\n/).filter(Boolean).slice(0, maxRows);
  }

  async function loadSyntheticPreview() {
    try {
      const [counts, metadata] = await Promise.all([
        parseCsvPreview(config.syntheticCountsUrl, 5),
        parseCsvPreview(config.syntheticMetadataUrl, 8),
      ]);
      const text = [
        "counts.csv preview:",
        ...counts,
        "",
        "metadata.csv preview:",
        ...metadata,
      ].join("\n");
      const preview = $("#synthetic-preview");
      if (preview) {
        preview.textContent = text;
      }
      setStatus(
        liveSubmitEnabled()
          ? "Synthetic preview loaded. Choose a workload size and click \"Run synthetic data through API\"."
          : "Synthetic toy dataset loaded for preview. Configure the API for live jobs.",
        "success",
      );
    } catch (error) {
      setStatus(error.message, "error");
    }
  }

  function renderTopGenes(rows) {
    const tbody = $("#top-genes-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      ["gene_id", "log2FoldChange", "padj", "baseMean"].forEach((key) => {
        const td = document.createElement("td");
        const value = row[key];
        td.textContent = typeof value === "number" ? value.toPrecision(4) : value;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
  }

  function artifactUrl(name) {
    return `${config.apiBaseUrl}/jobs/${state.jobId}/artifacts/${encodeURIComponent(name)}`;
  }

  function revokeBlobUrls() {
    state.blobUrls.forEach((url) => URL.revokeObjectURL(url));
    state.blobUrls = [];
  }

  function hideLiveResults() {
    revokeBlobUrls();
    $("#artifact-links")?.classList.add("is-hidden");
    $("#live-image-grid")?.classList.add("is-hidden");
    $("#result-csv-preview")?.classList.add("is-hidden");
    $("#result-csv-empty")?.classList.remove("is-hidden");
    $("#results-placeholder")?.classList.remove("is-hidden");
    const list = $("#live-artifacts");
    if (list) list.innerHTML = "";
    const grid = $("#live-image-grid");
    if (grid) grid.innerHTML = "";
    const csvPreview = $("#result-csv-preview");
    if (csvPreview) csvPreview.textContent = "";
    renderTopGenes([]);
    state.artifactsByName = {};
  }

  function mapArtifacts(artifacts) {
    const names = artifacts.map((artifact) => (typeof artifact === "string" ? artifact : artifact.name));
    state.artifactsByName = names.reduce((acc, name) => {
      acc[name] = artifactUrl(name);
      return acc;
    }, {});
    return names;
  }

  async function materializeBlobUrls(names) {
    await Promise.all(
      names.map(async (name) => {
        const sourceUrl = state.artifactsByName[name];
        const response = await fetch(sourceUrl, { headers: authHeaders() });
        if (!response.ok) throw new Error(`Could not fetch artifact ${name}`);
        const blob = await response.blob();
        const blobUrl = URL.createObjectURL(blob);
        state.blobUrls.push(blobUrl);
        state.artifactsByName[name] = blobUrl;
      }),
    );
  }

  function setLink(id, name) {
    const link = $(id);
    if (!link) return;
    const url = state.artifactsByName[name];
    if (!url) {
      link.classList.add("is-hidden");
      link.removeAttribute("href");
      return;
    }
    link.classList.remove("is-hidden");
    link.href = url;
  }

  function renderImageArtifacts(names) {
    const imageNames = names.filter((name) => /\.(png|jpg|jpeg|gif|webp)$/i.test(name));
    const grid = $("#live-image-grid");
    if (!grid) return;
    grid.innerHTML = "";
    if (!imageNames.length) {
      grid.classList.add("is-hidden");
      return;
    }
    imageNames.forEach((name) => {
      const figure = document.createElement("figure");
      const img = document.createElement("img");
      const caption = document.createElement("figcaption");
      img.src = state.artifactsByName[name];
      img.alt = name;
      caption.textContent = name;
      figure.appendChild(img);
      figure.appendChild(caption);
      grid.appendChild(figure);
    });
    grid.classList.remove("is-hidden");
  }

  async function renderCsvPreview() {
    const csvPreview = $("#result-csv-preview");
    const empty = $("#result-csv-empty");
    if (!csvPreview || !empty) return;

    const selected = ["top_genes.csv", "results.csv", "metadata_used.csv"].filter(
      (name) => state.artifactsByName[name],
    );
    if (!selected.length) {
      csvPreview.classList.add("is-hidden");
      empty.classList.remove("is-hidden");
      return;
    }

    const chunks = await Promise.all(
      selected.map(async (name) => {
        const rows = await parseCsvPreview(
          state.artifactsByName[name],
          name === "results.csv" ? 8 : 6,
        );
        return [`${name} preview:`, ...rows].join("\n");
      }),
    );
    csvPreview.textContent = chunks.join("\n\n");
    csvPreview.classList.remove("is-hidden");
    empty.classList.add("is-hidden");
  }

  async function renderArtifacts(artifacts) {
    const names = mapArtifacts(artifacts);
    await materializeBlobUrls(names);
    const list = $("#live-artifacts");
    if (!list) return;
    list.innerHTML = "";
    names.forEach((name) => {
      const li = document.createElement("li");
      const link = document.createElement("a");
      link.href = state.artifactsByName[name];
      link.textContent = name;
      link.target = "_blank";
      link.rel = "noopener";
      li.appendChild(link);
      list.appendChild(li);
    });
    setLink("#artifact-results", "results.csv");
    setLink("#artifact-top-genes", "top_genes.csv");
    setLink("#artifact-report", "report.html");
    $("#artifact-links")?.classList.remove("is-hidden");
    $("#results-placeholder")?.classList.add("is-hidden");
    renderImageArtifacts(names);
    await renderCsvPreview();
  }

  async function submitJob() {
    if (!liveSubmitEnabled()) {
      setStatus(
        "Live API is not enabled (demo mode or missing apiBaseUrl). Use http://127.0.0.1:4000 or localhost:4000 with Docker on :8000, or unset JEKYLL_ENV=production when running `jekyll serve`.",
        "info",
      );
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
        if (job.top_genes) renderTopGenes(job.top_genes);
        await renderArtifacts(job.artifacts || []);
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
    $("#use-synthetic")?.addEventListener("click", () => {
      loadSyntheticPreview().catch((error) => setStatus(error.message, "error"));
    });
    $("#run-synthetic")?.addEventListener("click", () =>
      submitJob().catch((error) => setStatus(error.message, "error")),
    );
    $("#poll-job")?.addEventListener("click", pollJob);
  }

  document.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    hideLiveResults();
    if (!liveSubmitEnabled()) {
      setStatus(
        "Demo mode: open via localhost / 127.0.0.1 and start Docker API on port 8000 for live runs.",
        "info",
      );
    } else {
      setStatus("Ready. Submit a synthetic job to generate run-specific outputs.", "info");
    }
  });
})();
