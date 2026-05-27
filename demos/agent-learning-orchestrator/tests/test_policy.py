"""Tests for reflect/adapt policy."""
from orchestrator.policy import (
    adapt_deseq,
    reflect_after_cycle,
)
from orchestrator.state import DeseqParams, CycleRecord


def test_reflect_finalize_clean_stable():
    cycle = CycleRecord(
        cycle_number=2,
        phase="reflect",
        contamination_verdict="no_strong_contamination_signal",
        top_genes_count=12,
        top_genes=["G1", "G2"],
    )
    stability = {"jaccard": 0.8, "stable": True}
    result = reflect_after_cycle(cycle=cycle, cycle_number=2, max_cycles=3, stability=stability)
    assert result["decision"] == "finalize"
    assert result["recommended_action"] == "proceed_to_downstream"


def test_reflect_retry_on_unstable():
    cycle = CycleRecord(
        cycle_number=1,
        phase="reflect",
        contamination_verdict="no_strong_contamination_signal",
        top_genes_count=8,
    )
    stability = {"jaccard": 0.2, "stable": False}
    result = reflect_after_cycle(cycle=cycle, cycle_number=1, max_cycles=3, stability=stability)
    assert result["decision"] == "retry_deseq"
    assert "unstable" in result["reason"].lower() or "changed" in result["reason"].lower()


def test_reflect_contamination_fail_escalates_at_cap():
    cycle = CycleRecord(
        cycle_number=3,
        phase="reflect",
        contamination_verdict="contaminant_likely",
        top_genes_count=0,
    )
    result = reflect_after_cycle(cycle=cycle, cycle_number=3, max_cycles=3, stability=None)
    assert result["decision"] == "finalize"
    assert result["recommended_action"] == "escalate_to_parent"


def test_adapt_deseq_empty_results():
    params = DeseqParams(min_count=10)
    new_params, change = adapt_deseq(params, empty_results=True, unstable=False)
    assert new_params.min_count == 5
    assert "min_count" in change
