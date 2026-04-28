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
    apiToken: "",
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

  async function parseCsvPreview(url, maxRows) {
    const response = await fetch(url);
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
          ? "Synthetic preview loaded. Click \"Run synthetic data through API\" to submit."
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

  async function loadSampleManifest() {
    try {
      const response = await fetch(config.sampleManifestUrl);
      if (!response.ok) throw new Error("Sample manifest is not available yet.");
      const manifest = await response.json();
      $("#sample-summary").textContent = `${manifest.sample_count} samples, ${manifest.gene_count} genes tested, ${manifest.significant_gene_count} significant at FDR 0.05.`;
      renderTopGenes(manifest.top_genes || []);
    } catch (error) {
      $("#sample-summary").textContent = error.message;
    }
  }

  async function uploadFiles() {
    const countsFile = $("#counts-file").files[0];
    const metadataFile = $("#metadata-file").files[0];
    if (!countsFile || !metadataFile) {
      throw new Error("Upload both counts.csv and metadata.csv, or use the synthetic dataset option.");
    }

    const form = new FormData();
    form.append("counts", countsFile);
    form.append("metadata", metadataFile);
    Object.entries(getFormValues()).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        form.append(key, String(value));
      }
    });

    const response = await fetch(`${config.apiBaseUrl}/uploads`, {
      method: "POST",
      headers: authHeaders(),
      body: form,
    });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  }

  async function submitJob(datasetMode) {
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
    let payload = getFormValues();
    if (datasetMode === "synthetic") {
      payload = {
        ...payload,
        dataset: "synthetic",
        counts_url: config.syntheticCountsUrl,
        metadata_url: config.syntheticMetadataUrl,
      };
    } else {
      const uploaded = await uploadFiles();
      payload = { ...payload, dataset: "uploaded", ...uploaded };
    }

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
    $("#job-id").textContent = state.jobId;
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
        renderArtifacts(job.artifacts || []);
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

  function renderArtifacts(artifacts) {
    const list = $("#live-artifacts");
    if (!list) return;
    list.innerHTML = "";
    artifacts.forEach((artifact) => {
      const name = typeof artifact === "string" ? artifact : artifact.name;
      const li = document.createElement("li");
      const link = document.createElement("a");
      link.href = `${config.apiBaseUrl}/jobs/${state.jobId}/artifacts/${encodeURIComponent(name)}`;
      link.textContent = name;
      link.target = "_blank";
      link.rel = "noopener";
      li.appendChild(link);
      list.appendChild(li);
    });
  }

  function bindEvents() {
    $("#use-synthetic")?.addEventListener("click", () => {
      loadSyntheticPreview().catch((error) => setStatus(error.message, "error"));
    });
    $("#run-synthetic")?.addEventListener("click", () =>
      submitJob("synthetic").catch((error) => setStatus(error.message, "error")),
    );
    $("#run-uploaded")?.addEventListener("click", () =>
      submitJob("uploaded").catch((error) => setStatus(error.message, "error")),
    );
    $("#poll-job")?.addEventListener("click", pollJob);
  }

  document.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    loadSampleManifest();
    if (!liveSubmitEnabled()) {
      setStatus(
        "Demo mode: sample outputs are shown below. On this machine open the site via localhost / 127.0.0.1 and start Docker API on port 8000 for live runs.",
        "info",
      );
    }
  });
})();
