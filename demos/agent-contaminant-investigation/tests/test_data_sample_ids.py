"""Synthetic data files must share the same sample_id namespace."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

SAMPLE_ID_TABLES = (
    "alignment_stats.csv",
    "sample_metrics.csv",
    "marker_hits.csv",
    "taxa_abundance.csv",
)


def _sample_ids(path: Path) -> set[str]:
    return set(pd.read_csv(path, usecols=["sample_id"])["sample_id"].astype(str))


def test_sample_ids_match_across_contamination_tables() -> None:
    paths = [DATA_DIR / name for name in SAMPLE_ID_TABLES]
    id_sets = [_sample_ids(path) for path in paths]
    reference = id_sets[0]
    assert reference, "expected at least one sample in alignment_stats.csv"
    for path, ids in zip(paths[1:], id_sets[1:]):
        assert ids == reference, f"sample_id mismatch in {path.name}"
