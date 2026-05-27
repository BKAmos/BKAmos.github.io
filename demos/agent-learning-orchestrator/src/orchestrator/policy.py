"""Reflect/adapt policy for the trust-and-DE micro-loop."""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Literal

from orchestrator.state import (
    STABILITY_JACCARD_THRESHOLD,
    ContamParams,
    CycleRecord,
    DeseqParams,
)

Decision = Literal["finalize", "retry_contamination", "retry_deseq"]

CLEAN_VERDICTS = {"no_strong_contamination_signal"}
FAIL_VERDICTS = {"contaminant_likely"}


def contamination_passes(verdict: str | None) -> bool:
    return verdict in CLEAN_VERDICTS


def extract_top_gene_ids(job_payload: dict[str, Any]) -> list[str]:
    genes: list[str] = []
    for row in job_payload.get("top_genes") or []:
        if isinstance(row, dict):
            gene = row.get("gene_id") or row.get("gene")
            if gene:
                genes.append(str(gene))
        elif isinstance(row, str):
            genes.append(row)
    return genes


def adapt_contamination(params: ContamParams, verdict: str | None) -> tuple[ContamParams, str]:
    if verdict in FAIL_VERDICTS and params.profile != "clean":
        return replace(params, profile="clean", strictness=min(params.strictness + 0.1, 1.0)), (
            f"profile {params.profile} -> clean; strictness -> {min(params.strictness + 0.1, 1.0):.1f}"
        )
    if verdict == "uncertain":
        new_strictness = min(params.strictness + 0.1, 1.0)
        return replace(params, strictness=new_strictness), f"strictness {params.strictness:.1f} -> {new_strictness:.1f}"
    new_strictness = max(params.strictness - 0.1, 0.1)
    return replace(params, strictness=new_strictness), f"strictness {params.strictness:.1f} -> {new_strictness:.1f}"


def adapt_deseq(params: DeseqParams, *, empty_results: bool, unstable: bool) -> tuple[DeseqParams, str]:
    if empty_results and params.min_count > 0:
        new_min = max(params.min_count - 5, 0)
        return replace(params, min_count=new_min), f"min_count {params.min_count} -> {new_min}"
    if empty_results and params.synthetic_profile == "small":
        return replace(params, synthetic_profile="medium"), "synthetic_profile small -> medium"
    if unstable and params.min_count > 0:
        new_min = max(params.min_count - 5, 0)
        return replace(params, min_count=new_min), f"min_count {params.min_count} -> {new_min} (stability retry)"
    if unstable and params.synthetic_profile != "large":
        order = ["small", "medium", "large"]
        idx = order.index(params.synthetic_profile)
        new_profile = order[min(idx + 1, len(order) - 1)]
        return replace(params, synthetic_profile=new_profile), f"synthetic_profile {params.synthetic_profile} -> {new_profile}"
    return params, "no further deseq adaptation"


def reflect_after_cycle(
    *,
    cycle: CycleRecord,
    cycle_number: int,
    max_cycles: int,
    stability: dict[str, Any] | None,
) -> dict[str, Any]:
    verdict = cycle.contamination_verdict
    top_count = cycle.top_genes_count
    stable = stability["stable"] if stability else True

    if verdict in FAIL_VERDICTS:
        if cycle_number >= max_cycles:
            return _decision(
                "finalize",
                "Contamination concern persists after max internal cycles.",
                "escalate_to_parent",
                confidence=0.35,
                blocking=["contamination_verdict_not_clean"],
            )
        return _decision(
            "retry_contamination",
            "Contamination verdict requires QC parameter adjustment before DE.",
            "recollect_or_resequence",
            confidence=0.45,
            blocking=["contamination_verdict_not_clean"],
        )

    if verdict == "uncertain":
        if cycle_number >= max_cycles:
            return _decision(
                "finalize",
                "Contamination verdict remained uncertain at iteration cap.",
                "escalate_to_parent",
                confidence=0.5,
                blocking=["contamination_verdict_uncertain"],
            )
        return _decision(
            "retry_contamination",
            "Uncertain contamination signal; tightening QC parameters.",
            "recollect_or_resequence",
            confidence=0.55,
            blocking=["contamination_verdict_uncertain"],
        )

    if top_count == 0:
        if cycle_number >= max_cycles:
            return _decision(
                "finalize",
                "No DE hits after max internal cycles.",
                "review_design_or_depth",
                confidence=0.4,
                blocking=["de_results_empty"],
            )
        return _decision(
            "retry_deseq",
            "DE returned no top genes; relaxing filters.",
            "review_design_or_depth",
            confidence=0.55,
            blocking=["de_results_empty"],
        )

    if stability and not stable:
        if cycle_number >= max_cycles:
            return _decision(
                "finalize",
                f"DE top genes unstable (Jaccard {stability['jaccard']:.2f} < {STABILITY_JACCARD_THRESHOLD}).",
                "escalate_to_parent",
                confidence=0.6,
                blocking=["de_results_unstable"],
            )
        return _decision(
            "retry_deseq",
            f"DE top genes changed materially (Jaccard {stability['jaccard']:.2f}); adapting DE params.",
            "review_design_or_depth",
            confidence=0.65,
            blocking=["de_results_unstable"],
        )

    confidence = 0.75
    if stability:
        confidence = min(0.95, 0.7 + 0.25 * stability["jaccard"])
    return _decision(
        "finalize",
        "Contamination clean and DE results stable enough to hand off.",
        "proceed_to_downstream",
        confidence=confidence,
        blocking=[],
    )


def _decision(
    decision: Decision,
    reason: str,
    recommended_action: str,
    *,
    confidence: float,
    blocking: list[str],
) -> dict[str, Any]:
    return {
        "decision": decision,
        "reason": reason,
        "recommended_action": recommended_action,
        "confidence": round(confidence, 3),
        "blocking_issues": blocking,
    }
