"""Execute the trust-and-DE micro-loop."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from orchestrator.delegates import SubAgentClient, SubAgentError
from orchestrator.handoff import build_component_summary
from orchestrator.policy import (
    adapt_contamination,
    adapt_deseq,
    contamination_passes,
    extract_top_gene_ids,
    reflect_after_cycle,
)
from orchestrator.stability import compare_top_genes
from orchestrator.study_service import ensure_study_bundle, finalize_study_for_run, refresh_study_contam_profile
from orchestrator.state import (
    STABILITY_JACCARD_THRESHOLD,
    STABILITY_TOP_N,
    CycleRecord,
    ComponentRun,
)


def _finalize_run(run: ComponentRun, studies_dir: Path) -> ComponentRun:
    finalize_study_for_run(run, studies_dir)
    return run


def run_component_loop(client: SubAgentClient, run: ComponentRun, *, studies_dir: Path) -> ComponentRun:
    run.status = "running"
    run.phase = "micro_loop"
    ensure_study_bundle(run, studies_dir)

    while run.internal_cycles_run < run.max_internal_cycles:
        run.internal_cycles_run += 1
        cycle_number = run.internal_cycles_run
        adaptations: list[str] = []

        cycle = CycleRecord(cycle_number=cycle_number, phase="contamination")
        run.phase = f"cycle_{cycle_number}_contamination"

        try:
            contam_payload = client.run_contamination(
                run.contam_params,
                study_id=run.study_id,
                inputs_dir=run.study_inputs_dir,
            )
        except SubAgentError as exc:
            run.status = "failed"
            run.phase = "failed"
            run.message = str(exc)
            return run

        cycle.contamination_job_id = contam_payload.get("job_id")
        verdict_payload = contam_payload.get("verdict") or {}
        cycle.contamination_verdict = verdict_payload.get("verdict")
        cycle.contamination_confidence = verdict_payload.get("confidence")

        if not contamination_passes(cycle.contamination_verdict):
            reflection = reflect_after_cycle(
                cycle=cycle,
                cycle_number=cycle_number,
                max_cycles=run.max_internal_cycles,
                stability=None,
            )
            cycle.phase = "reflect"
            run.cycles.append(cycle)
            if reflection["decision"] == "retry_contamination" and cycle_number < run.max_internal_cycles:
                new_params, change = adapt_contamination(run.contam_params, cycle.contamination_verdict)
                run.contam_params = new_params
                refresh_study_contam_profile(run, studies_dir)
                run.adaptations_applied.append({"cycle": cycle_number, "change": change})
                continue
            run.component_summary = build_component_summary(run, reflection)
            run.status = "finalized"
            run.phase = "finalized"
            return _finalize_run(run, studies_dir)

        run.phase = f"cycle_{cycle_number}_deseq"
        cycle.phase = "deseq"
        try:
            deseq_payload = client.run_deseq(
                run.deseq_params,
                study_id=run.study_id,
                inputs_dir=run.study_inputs_dir,
            )
        except SubAgentError as exc:
            run.status = "failed"
            run.phase = "failed"
            run.message = str(exc)
            return run

        cycle.deseq_job_id = deseq_payload.get("job_id")
        cycle.top_genes = extract_top_gene_ids(deseq_payload)
        cycle.top_genes_count = len(cycle.top_genes)

        stability = None
        if run.previous_top_genes:
            stability = compare_top_genes(
                run.previous_top_genes,
                cycle.top_genes,
                top_n=STABILITY_TOP_N,
                stable_threshold=STABILITY_JACCARD_THRESHOLD,
            )
        cycle.stability = stability

        partial_snapshot = _cycle_snapshot(run, cycle, reflection=None)
        run.phase = f"cycle_{cycle_number}_report"
        cycle.phase = "report"
        try:
            report_payload = client.run_cycle_report(partial_snapshot)
            cycle.report_job_id = report_payload.get("job_id")
        except SubAgentError:
            cycle.report_job_id = None

        reflection = reflect_after_cycle(
            cycle=cycle,
            cycle_number=cycle_number,
            max_cycles=run.max_internal_cycles,
            stability=stability,
        )
        cycle.phase = "reflect"
        cycle.adaptations_from_previous = adaptations
        run.cycles.append(cycle)
        run.previous_top_genes = cycle.top_genes

        if reflection["decision"] == "finalize":
            run.component_summary = build_component_summary(run, reflection)
            run.status = "finalized"
            run.phase = "finalized"
            return _finalize_run(run, studies_dir)

        if reflection["decision"] == "retry_contamination" and cycle_number < run.max_internal_cycles:
            new_params, change = adapt_contamination(run.contam_params, cycle.contamination_verdict)
            run.contam_params = new_params
            refresh_study_contam_profile(run, studies_dir)
            run.adaptations_applied.append({"cycle": cycle_number, "change": change})
            continue

        if reflection["decision"] == "retry_deseq" and cycle_number < run.max_internal_cycles:
            unstable = bool(stability and not stability.get("stable"))
            new_params, change = adapt_deseq(
                run.deseq_params,
                empty_results=cycle.top_genes_count == 0,
                unstable=unstable,
            )
            run.deseq_params = new_params
            run.adaptations_applied.append({"cycle": cycle_number, "change": change})
            continue

        run.component_summary = build_component_summary(run, reflection)
        run.status = "finalized"
        run.phase = "finalized"
        return _finalize_run(run, studies_dir)

    last_reflection = reflect_after_cycle(
        cycle=run.cycles[-1],
        cycle_number=run.internal_cycles_run,
        max_cycles=run.max_internal_cycles,
        stability=run.cycles[-1].stability if run.cycles else None,
    )
    run.component_summary = build_component_summary(run, last_reflection)
    run.status = "finalized"
    run.phase = "finalized"
    return _finalize_run(run, studies_dir)


def _cycle_snapshot(run: ComponentRun, cycle: CycleRecord, reflection: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "component_run_id": run.component_run_id,
        "cycle_number": cycle.cycle_number,
        "contamination": {
            "job_id": cycle.contamination_job_id,
            "verdict": cycle.contamination_verdict,
            "confidence": cycle.contamination_confidence,
            "params": asdict(run.contam_params),
        },
        "expression": {
            "job_id": cycle.deseq_job_id,
            "top_genes": cycle.top_genes[:10],
            "top_genes_count": cycle.top_genes_count,
            "params": asdict(run.deseq_params),
        },
        "stability": cycle.stability,
        "reflection": reflection,
        "adaptations_applied": run.adaptations_applied,
    }


def save_run(run_dir: Path, run: ComponentRun) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "component_run_id": run.component_run_id,
        "status": run.status,
        "phase": run.phase,
        "internal_cycles_run": run.internal_cycles_run,
        "max_internal_cycles": run.max_internal_cycles,
        "study_id": run.study_id,
        "study_inputs_dir": run.study_inputs_dir,
        "requested_contam_profile": run.requested_contam_profile,
        "contam_params": asdict(run.contam_params),
        "deseq_params": asdict(run.deseq_params),
        "adaptations_applied": run.adaptations_applied,
        "cycles": [asdict(cycle) for cycle in run.cycles],
        "component_summary": run.component_summary,
        "message": run.message,
    }
    (run_dir / "run_state.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if run.component_summary:
        (run_dir / "component_summary.json").write_text(
            json.dumps(run.component_summary, indent=2),
            encoding="utf-8",
        )


def load_run(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "run_state.json"
    if not path.exists():
        raise FileNotFoundError(f"Run not found: {run_dir.name}")
    return json.loads(path.read_text(encoding="utf-8"))
