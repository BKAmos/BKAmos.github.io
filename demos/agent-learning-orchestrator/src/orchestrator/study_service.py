"""Ensure shared study bundle exists for a component run."""
from __future__ import annotations

import uuid
from pathlib import Path

from orchestrator.state import ComponentRun
from orchestrator.study_bundle import (
    DESEQ_PROFILES,
    finalize_study_manifest,
    refresh_contam_profile,
    write_study_bundle,
)


def ensure_study_bundle(run: ComponentRun, studies_dir: Path) -> None:
    if not run.study_id:
        run.study_id = uuid.uuid4().hex[:12]
    study_dir = studies_dir / run.study_id
    manifest_path = study_dir / "study_manifest.json"
    if manifest_path.exists():
        run.study_inputs_dir = str(study_dir.resolve())
        return

    deseq_spec = DESEQ_PROFILES[run.deseq_params.synthetic_profile]
    run.contam_params.sample_count = deseq_spec["samples"]
    run.requested_contam_profile = run.contam_params.profile

    manifest = write_study_bundle(
        study_dir,
        study_id=run.study_id,
        contam_profile=run.contam_params.profile,
        deseq_profile=run.deseq_params.synthetic_profile,
        cohort_seed=run.contam_params.synthetic_seed,
        sample_count=run.contam_params.sample_count,
        expression_seed=run.deseq_params.synthetic_seed,
    )
    run.study_inputs_dir = manifest["inputs_dir"]


def refresh_study_contam_profile(run: ComponentRun, studies_dir: Path) -> None:
    if not run.study_id:
        raise ValueError("study_id is required to refresh contamination views")
    study_dir = studies_dir / run.study_id
    refresh_contam_profile(
        study_dir,
        profile=run.contam_params.profile,
        cohort_seed=run.contam_params.synthetic_seed,
    )
    run.study_inputs_dir = str(study_dir.resolve())


def finalize_study_for_run(run: ComponentRun, studies_dir: Path) -> None:
    if not run.study_id:
        return
    study_dir = studies_dir / run.study_id
    finalize_study_manifest(study_dir, effective_contam_profile=run.contam_params.profile)
    run.study_inputs_dir = str(study_dir.resolve())
