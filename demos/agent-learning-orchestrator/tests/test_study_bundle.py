"""Tests for shared study bundle generation."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from orchestrator.study_bundle import write_study_bundle


def test_write_study_bundle_aligns_sample_ids(tmp_path: Path) -> None:
    study_dir = tmp_path / "study01"
    manifest = write_study_bundle(
        study_dir,
        study_id="study01",
        contam_profile="low_contam",
        deseq_profile="medium",
        cohort_seed=42,
    )

    metadata = pd.read_csv(study_dir / "metadata.csv")
    counts = pd.read_csv(study_dir / "counts.csv", index_col=0)
    alignment = pd.read_csv(study_dir / "alignment_stats.csv")

    assert manifest["sample_ids"] == metadata["sample_id"].tolist()
    assert list(counts.columns) == manifest["sample_ids"]
    assert alignment["sample_id"].tolist() == manifest["sample_ids"]
    assert (study_dir / "study_manifest.json").exists()


def test_refresh_contam_profile_preserves_requested_profile(tmp_path: Path) -> None:
    from orchestrator.study_bundle import refresh_contam_profile

    study_dir = tmp_path / "study02"
    write_study_bundle(
        study_dir,
        study_id="study02",
        contam_profile="high_contam",
        deseq_profile="medium",
        cohort_seed=42,
    )
    refresh_contam_profile(study_dir, profile="clean", cohort_seed=42)
    manifest = json.loads((study_dir / "study_manifest.json").read_text(encoding="utf-8"))
    profile_manifest = json.loads((study_dir / "profile_manifest.json").read_text(encoding="utf-8"))

    assert manifest["requested_contam_profile"] == "high_contam"
    assert manifest["effective_contam_profile"] == "clean"
    assert profile_manifest["profile"] == "clean"
