from __future__ import annotations

import pytest

from worker.run_job import InvestigationConfig, _score_evidence


def evidence(
    *,
    max_ratio: float,
    max_marker: int = 0,
    max_control: int = 0,
) -> dict[str, list[dict[str, float | int | str]]]:
    return {
        "non_host_ratio_by_sample": [{"sample_id": "S1", "non_host_ratio": max_ratio}],
        "unexpected_marker_hits": [{"sample_id": "S1", "marker_name": "marker", "hit_count": max_marker}],
        "negative_control_bleed": [{"sample_id": "NEG", "contaminant_reads": max_control}],
    }


def test_score_evidence_classifies_low_signal_as_clean() -> None:
    score = _score_evidence(evidence(max_ratio=0.01), strictness=0.6)

    assert score["verdict"] == "no_strong_contamination_signal"
    assert score["risk_score"] < 18
    assert score["confidence"] == pytest.approx(0.1)


def test_score_evidence_classifies_middle_signal_as_uncertain() -> None:
    score = _score_evidence(evidence(max_ratio=0.4), strictness=0.6)

    assert score["verdict"] == "uncertain"
    assert 18 <= score["risk_score"] < 49.2


def test_score_evidence_classifies_marker_and_control_signal_as_likely_contaminant() -> None:
    score = _score_evidence(
        evidence(max_ratio=0.7, max_marker=2, max_control=5_000),
        strictness=0.6,
    )

    assert score["verdict"] == "contaminant_likely"
    assert score["risk_score"] >= 49.2


def test_investigation_config_rejects_out_of_range_iteration_counts() -> None:
    with pytest.raises(ValueError, match="max_iterations must be between 1 and 3"):
        InvestigationConfig(max_iterations=4)
