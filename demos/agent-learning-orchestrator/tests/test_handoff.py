"""Tests for component handoff summary."""
from orchestrator.handoff import build_component_summary
from orchestrator.state import ComponentRun, CycleRecord, DeseqParams


def test_build_component_summary_includes_handoff():
    run = ComponentRun(component_run_id="abc123", internal_cycles_run=2)
    run.deseq_params = DeseqParams(synthetic_profile="medium", min_count=5)
    run.cycles.append(
        CycleRecord(
            cycle_number=2,
            phase="reflect",
            contamination_job_id="c1",
            contamination_verdict="no_strong_contamination_signal",
            deseq_job_id="d1",
            top_genes=["G1", "G2"],
            top_genes_count=2,
            report_job_id="r1",
            stability={"jaccard": 0.75, "stable": True, "top_n": 10},
        )
    )
    reflection = {
        "decision": "finalize",
        "reason": "Stable DE",
        "recommended_action": "proceed_to_downstream",
        "confidence": 0.82,
        "blocking_issues": [],
    }
    summary = build_component_summary(run, reflection)
    assert summary["component_id"] == "rna-seq-trust-de"
    assert summary["parent_handoff"]["recommended_action"] == "proceed_to_downstream"
    assert summary["stability"]["jaccard"] == 0.75
    assert summary["expression"]["params_used"]["min_count"] == 5
