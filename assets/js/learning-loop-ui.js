(function () {
  "use strict";

  const cfg = window.LEARNING_LOOP_CONFIG || {};
  const onLoopback = /^localhost$/i.test(window.location.hostname) || window.location.hostname === "127.0.0.1";
  if (onLoopback && !cfg.apiBaseUrl) cfg.apiBaseUrl = "http://localhost:8003";
  const sampleSummaryBase =
    cfg.sampleSummaryBase || "/demos/agent-learning-orchestrator/outputs/component_summary.json";

  const SAMPLE_SUMMARY = {
    component_id: "rna-seq-trust-de",
    component_run_id: "sample-run",
    status: "finalized",
    confidence: 0.84,
    internal_cycles_run: 2,
    max_internal_cycles: 3,
    study: {
      study_id: "sample-study",
      study_inputs_dir: "demos/_shared_studies/sample-study",
      requested_contam_profile: "low_contam",
      effective_contam_profile: "clean",
      deseq_profile: "medium",
    },
    trust: { contamination_verdict: "no_strong_contamination_signal" },
    expression: { top_genes_count: 10, params_used: { synthetic_profile: "medium", min_count: 5 } },
    stability: { jaccard: 0.3333, stable: false, overlap_count: 4, top_n: 10 },
    parent_handoff: {
      recommended_action: "proceed_to_downstream",
      blocking_issues: [],
      suggested_next_components: ["pathway-interpretation", "multimodal-validation"],
    },
    reflection: {
      reason: "Contamination clean; DE stabilized after min_count adaptation.",
      adaptations_applied: [{ cycle: 1, change: "min_count 10 → 5 (stability retry)" }],
    },
    cycles: [
      { cycle_number: 1, contamination_verdict: "no_strong_contamination_signal", top_genes_count: 10, stability: null },
      {
        cycle_number: 2,
        contamination_verdict: "no_strong_contamination_signal",
        top_genes_count: 10,
        stability: { jaccard: 0.3333, stable: false },
      },
    ],
  };

  function $(sel) {
    return document.querySelector(sel);
  }

  function isDemoMode() {
    return cfg.demoMode === true || !cfg.apiBaseUrl;
  }

  function setStatus(message, kind) {
    const el = $("#learning-loop-status");
    if (!el) return;
    el.textContent = message;
    el.dataset.kind = kind || "info";
  }

  function authHeaders() {
    const token = $("#api-token")?.value?.trim();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  function renderTimeline(cycles) {
    const list = $("#cycle-timeline-list");
    if (!list) return;
    list.innerHTML = "";
    (cycles || []).forEach(function (cycle) {
      const li = document.createElement("li");
      const stability = cycle.stability
        ? ` · stability Jaccard ${cycle.stability.jaccard}${cycle.stability.stable ? " (stable)" : " (unstable)"}`
        : "";
      li.textContent = `Cycle ${cycle.cycle_number}: QC ${cycle.contamination_verdict || "n/a"} · DE hits ${cycle.top_genes_count ?? "n/a"}${stability}`;
      list.appendChild(li);
    });
  }

  function renderCompare(cycles) {
    const container = $("#cycle-compare");
    if (!container || !cycles || cycles.length < 2) {
      if (container) container.innerHTML = "<p class=\"portfolio-meta\">Run at least two internal cycles to compare adaptations.</p>";
      return;
    }
    const first = cycles[0];
    const last = cycles[cycles.length - 1];
    container.innerHTML = [
      "<section><h3>Cycle 1</h3>",
      `<p>QC: <span class="learning-loop-pill">${first.contamination_verdict || "n/a"}</span></p>`,
      `<p>DE hits: ${first.top_genes_count ?? "n/a"}</p>`,
      "</section>",
      "<section><h3>Cycle " + last.cycle_number + "</h3>",
      `<p>QC: <span class="learning-loop-pill">${last.contamination_verdict || "n/a"}</span></p>`,
      `<p>DE hits: ${last.top_genes_count ?? "n/a"}</p>`,
      last.stability
        ? `<p>Stability: Jaccard ${last.stability.jaccard} (${last.stability.stable ? "stable" : "unstable"})</p>`
        : "",
      "</section>",
    ].join("");
  }

  function renderHandoff(summary) {
    const actionEl = $("#handoff-action");
    const metaEl = $("#handoff-meta");
    const jsonEl = $("#handoff-json");
    const blockingEl = $("#handoff-blocking");
    const nextEl = $("#handoff-next-components");
    if (!summary) return;

    if (actionEl) actionEl.textContent = summary.parent_handoff?.recommended_action || "pending";
    if (metaEl) {
      const study = summary.study || {};
      const requestedProfile = study.requested_contam_profile;
      const effectiveProfile = study.effective_contam_profile;
      const profileLine =
        requestedProfile && effectiveProfile && requestedProfile !== effectiveProfile
          ? `QC profile ${requestedProfile} → ${effectiveProfile} (adapted)`
          : requestedProfile
            ? `QC profile ${requestedProfile}`
            : null;
      metaEl.textContent = [
        `Confidence ${summary.confidence ?? "n/a"}`,
        `${summary.internal_cycles_run ?? 0} internal cycle(s)`,
        summary.trust?.contamination_verdict ? `QC ${summary.trust.contamination_verdict}` : null,
        profileLine,
        study.study_id ? `Study ${study.study_id}` : null,
      ]
        .filter(Boolean)
        .join(" · ");
    }
    if (blockingEl) {
      const issues = summary.parent_handoff?.blocking_issues || [];
      blockingEl.textContent = issues.length ? issues.join(", ") : "None";
    }
    if (nextEl) {
      nextEl.innerHTML = "";
      (summary.parent_handoff?.suggested_next_components || []).forEach(function (name) {
        const li = document.createElement("li");
        li.textContent = name;
        nextEl.appendChild(li);
      });
    }
    if (jsonEl) jsonEl.textContent = JSON.stringify(summary, null, 2);

    renderTimeline(summary.cycles || []);
    renderCompare(summary.cycles || []);
  }

  async function loadSampleSummary() {
    try {
      const response = await fetch(sampleSummaryBase);
      if (response.ok) {
        renderHandoff(await response.json());
        return;
      }
    } catch (_err) {
      /* fall through */
    }
    renderHandoff(SAMPLE_SUMMARY);
  }

  async function runComponent() {
    if (isDemoMode()) {
      setStatus("Demo mode: showing sample component summary.", "info");
      await loadSampleSummary();
      return;
    }

    setStatus("Starting component run…", "info");
    const maxCycles = Number($("#max-cycles")?.value || 3);
    const body = {
      max_internal_cycles: maxCycles,
      contamination: {
        profile: $("#contam-profile")?.value || "low_contam",
        strictness: Number($("#contam-strictness")?.value || 0.6),
      },
      deseq: {
        synthetic_profile: $("#deseq-profile")?.value || "medium",
        min_count: Number($("#deseq-min-count")?.value || 10),
      },
    };

    try {
      const response = await fetch(`${cfg.apiBaseUrl.replace(/\/$/, "")}/tools/start_component`, {
        method: "POST",
        headers: Object.assign({ "Content-Type": "application/json" }, authHeaders()),
        body: JSON.stringify(body),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || response.statusText);

      $("#component-run-id").textContent = payload.component_run_id || "n/a";
      $("#component-status").textContent = payload.status || "unknown";
      $("#component-phase").textContent = payload.phase || "n/a";

      if (payload.component_summary) {
        renderHandoff(payload.component_summary);
      } else if (payload.summary_url) {
        const summaryResp = await fetch(`${cfg.apiBaseUrl.replace(/\/$/, "")}${payload.summary_url}`, {
          headers: authHeaders(),
        });
        renderHandoff(await summaryResp.json());
      }
      setStatus("Component run completed.", "success");
    } catch (err) {
      setStatus(String(err.message || err), "error");
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    const note = $("#learning-loop-demo-note");
    if (note) note.hidden = !isDemoMode();
    if (isDemoMode()) {
      setStatus("Published demo mode: sample handoff summary loaded.", "info");
      loadSampleSummary();
    } else {
      setStatus("Live mode: orchestrator API connected.", "success");
    }
    $("#run-component")?.addEventListener("click", runComponent);
  });
})();
