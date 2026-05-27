"""Component run state for the RNA-seq trust-and-DE micro-loop."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


COMPONENT_ID = "rna-seq-trust-de"
COMPONENT_VERSION = "0.1.0"
MAX_INTERNAL_CYCLES = 3
STABILITY_TOP_N = 10
STABILITY_JACCARD_THRESHOLD = 0.5


@dataclass
class ContamParams:
    profile: str = "low_contam"
    sample_count: int = 24
    synthetic_seed: int = 42
    strictness: float = 0.6
    max_iterations: int = 2


@dataclass
class DeseqParams:
    synthetic_profile: str = "medium"
    synthetic_seed: int | None = None
    condition_column: str = "condition"
    reference_level: str = "control"
    treatment_level: str = "treated"
    batch_column: str | None = "batch"
    min_count: int = 10


@dataclass
class CycleRecord:
    cycle_number: int
    phase: str
    contamination_job_id: str | None = None
    contamination_verdict: str | None = None
    contamination_confidence: float | None = None
    deseq_job_id: str | None = None
    top_genes: list[str] = field(default_factory=list)
    top_genes_count: int = 0
    report_job_id: str | None = None
    stability: dict[str, Any] | None = None
    adaptations_from_previous: list[str] = field(default_factory=list)


@dataclass
class ComponentRun:
    component_run_id: str
    status: str = "pending"
    phase: str = "pending"
    max_internal_cycles: int = MAX_INTERNAL_CYCLES
    internal_cycles_run: int = 0
    study_id: str | None = None
    study_inputs_dir: str | None = None
    requested_contam_profile: str | None = None
    contam_params: ContamParams = field(default_factory=ContamParams)
    deseq_params: DeseqParams = field(default_factory=DeseqParams)
    cycles: list[CycleRecord] = field(default_factory=list)
    adaptations_applied: list[dict[str, Any]] = field(default_factory=list)
    previous_top_genes: list[str] = field(default_factory=list)
    component_summary: dict[str, Any] | None = None
    message: str = ""
