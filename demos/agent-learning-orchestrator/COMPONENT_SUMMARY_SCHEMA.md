# component_summary.json schema

Primary handoff artifact from the RNA-seq trust-and-DE micro-loop to a parent orchestrator.

## Top-level fields

| Field | Type | Description |
|-------|------|-------------|
| `component_id` | string | Always `rna-seq-trust-de` |
| `component_version` | string | Semver of this component (e.g. `0.1.0`) |
| `component_run_id` | string | Unique run identifier |
| `status` | string | `finalized`, `failed`, or `running` |
| `confidence` | number | 0–1 internal confidence (stability + gate signals, not biological truth) |
| `internal_cycles_run` | integer | Completed internal cycles (≤ `max_internal_cycles`) |
| `max_internal_cycles` | integer | Cap on internal iterations (1–3) |
| `study` | object | Shared synthetic study bundle used by contamination and DESeq |
| `trust` | object | Contamination QC gate outcome |
| `expression` | object | DESeq results under final parameters |
| `stability` | object \| null | Jaccard top-10 comparison vs previous cycle |
| `report` | object | Cycle report agent job reference |
| `cycles` | array | Per-cycle timeline for debugging |
| `reflection` | object | Orchestrator reflect/adapt decision |
| `parent_handoff` | object | **Integration surface for parent orchestrator** |

## study

```json
{
  "study_id": "abc123",
  "study_inputs_dir": "demos/_shared_studies/abc123",
  "requested_contam_profile": "low_contam",
  "effective_contam_profile": "clean",
  "deseq_profile": "medium"
}
```

The orchestrator writes one shared synthetic cohort bundle per component run. Both contamination QC and DESeq receive the same `inputs_dir` so the trust gate and expression result describe the same samples. `effective_contam_profile` may differ from `requested_contam_profile` if the loop adapts QC inputs across internal cycles.

## trust

```json
{
  "contamination_verdict": "no_strong_contamination_signal",
  "contamination_job_id": "abc123",
  "artifacts": ["verdict.json", "timeline.json"]
}
```

Verdict values mirror the contamination sub-agent: `no_strong_contamination_signal`, `contaminant_likely`, `uncertain`.

## expression

```json
{
  "deseq_job_id": "deseq01",
  "top_genes_count": 12,
  "top_genes": ["GENE_1", "GENE_2"],
  "params_used": {
    "synthetic_profile": "medium",
    "min_count": 5,
    "condition_column": "condition",
    "reference_level": "control",
    "treatment_level": "treated",
    "batch_column": "batch"
  },
  "artifacts": ["results.csv", "volcano.png", "top_genes.csv"]
}
```

## stability

Present when at least two internal cycles completed a DESeq step.

```json
{
  "top_n": 10,
  "previous_genes": ["GENE_01", "..."],
  "current_genes": ["GENE_12", "..."],
  "jaccard": 0.3333,
  "stable": false,
  "overlap_count": 4
}
```

`stable` is `true` when `jaccard >= 0.5` (configurable via `STABILITY_JACCARD_THRESHOLD`).

## parent_handoff

```json
{
  "recommended_action": "proceed_to_downstream",
  "blocking_issues": [],
  "suggested_next_components": ["pathway-interpretation", "multimodal-validation"],
  "notes": "Synthetic demo only; parent should map actions to real study context."
}
```

### recommended_action values

| Value | Meaning |
|-------|---------|
| `proceed_to_downstream` | Trust + DE stable enough to continue |
| `recollect_or_resequence` | Contamination concern; QC retry exhausted or inconclusive |
| `review_design_or_depth` | Clean QC but empty or unstable DE |
| `escalate_to_parent` | Max internal cycles reached with unresolved issues |

`suggested_next_components` are **string hints only** — not wired in this repo.

## MCP / REST access

- `POST /tools/start_component` — start run; response includes inline `component_summary` when finalized
- `GET /components/{component_run_id}/summary` — fetch handoff payload
- `POST /tools/submit_to_parent` — POST finalized summary to `PARENT_ORCHESTRATOR_URL` (or `parent_url` in body)
- MCP tools: `start_component`, `get_component_status`, `get_component_summary`, `submit_to_parent`

Sample checked in for published demo mode: [`outputs/component_summary.json`](outputs/component_summary.json).
