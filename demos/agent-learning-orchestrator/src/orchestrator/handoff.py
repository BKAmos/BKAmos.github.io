"""Build component_summary.json for parent orchestrator handoff."""
from __future__ import annotations

from typing import Any

from orchestrator.state import COMPONENT_ID, COMPONENT_VERSION, ComponentRun


def build_component_summary(run: ComponentRun, reflection: dict[str, Any]) -> dict[str, Any]:
    last_cycle = run.cycles[-1] if run.cycles else None
    trust_verdict = last_cycle.contamination_verdict if last_cycle else None
    deseq_job_id = last_cycle.deseq_job_id if last_cycle else None
    report_job_id = last_cycle.report_job_id if last_cycle else None

    suggested_next = ["pathway-interpretation", "multimodal-validation"]
    if reflection.get("recommended_action") == "escalate_to_parent":
        suggested_next = ["parent-review", "wet-lab-qc"]
    elif reflection.get("recommended_action") == "recollect_or_resequence":
        suggested_next = ["sample-recollection", "resequence-qc"]

    summary = {
        "component_id": COMPONENT_ID,
        "component_version": COMPONENT_VERSION,
        "component_run_id": run.component_run_id,
        "status": run.status,
        "confidence": reflection.get("confidence", 0.0),
        "internal_cycles_run": run.internal_cycles_run,
        "max_internal_cycles": run.max_internal_cycles,
        "study": {
            "study_id": run.study_id,
            "study_inputs_dir": run.study_inputs_dir,
            "requested_contam_profile": run.requested_contam_profile,
            "effective_contam_profile": run.contam_params.profile,
            "deseq_profile": run.deseq_params.synthetic_profile,
        },
        "trust": {
            "contamination_verdict": trust_verdict,
            "contamination_job_id": last_cycle.contamination_job_id if last_cycle else None,
            "artifacts": ["verdict.json", "timeline.json"],
        },
        "expression": {
            "deseq_job_id": deseq_job_id,
            "top_genes_count": last_cycle.top_genes_count if last_cycle else 0,
            "top_genes": (last_cycle.top_genes[:10] if last_cycle else []),
            "params_used": _deseq_params_dict(run),
            "artifacts": ["results.csv", "volcano.png", "top_genes.csv"],
        },
        "stability": last_cycle.stability if last_cycle else None,
        "report": {
            "job_id": report_job_id,
            "artifacts": ["cycle_report.html", "cycle_report.json"],
        },
        "cycles": [
            {
                "cycle_number": cycle.cycle_number,
                "contamination_verdict": cycle.contamination_verdict,
                "deseq_job_id": cycle.deseq_job_id,
                "top_genes_count": cycle.top_genes_count,
                "stability": cycle.stability,
                "adaptations_from_previous": cycle.adaptations_from_previous,
            }
            for cycle in run.cycles
        ],
        "reflection": {
            "decision": reflection.get("decision"),
            "reason": reflection.get("reason"),
            "adaptations_applied": run.adaptations_applied,
        },
        "parent_handoff": {
            "recommended_action": reflection.get("recommended_action"),
            "blocking_issues": reflection.get("blocking_issues", []),
            "suggested_next_components": suggested_next,
            "notes": "Synthetic demo only; parent should map actions to real study context.",
        },
    }
    return summary


def _deseq_params_dict(run: ComponentRun) -> dict[str, Any]:
    params = run.deseq_params
    return {
        "synthetic_profile": params.synthetic_profile,
        "min_count": params.min_count,
        "condition_column": params.condition_column,
        "reference_level": params.reference_level,
        "treatment_level": params.treatment_level,
        "batch_column": params.batch_column,
    }
