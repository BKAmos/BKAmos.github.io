"""Unit tests for cycle report rendering (no FastAPI)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from run_cycle_report import render_cycle_report  # noqa: E402

SAMPLE_SNAPSHOT = {
    "component_run_id": "test-run",
    "cycle_number": 1,
    "contamination": {
        "job_id": "c1",
        "verdict": "no_strong_contamination_signal",
        "confidence": 0.82,
        "params": {"profile": "low_contam", "strictness": 0.6},
    },
    "expression": {
        "job_id": "d1",
        "top_genes": ["GENE_1", "GENE_2"],
        "top_genes_count": 2,
        "params": {"synthetic_profile": "medium", "min_count": 10},
    },
    "stability": None,
    "adaptations_applied": [],
}


def test_render_cycle_report_writes_artifacts(tmp_path):
    manifest = render_cycle_report(tmp_path, SAMPLE_SNAPSHOT, "job01")
    assert manifest["status"] == "completed"
    assert (tmp_path / "cycle_report.html").exists()
    assert (tmp_path / "cycle_report.json").exists()
    html = (tmp_path / "cycle_report.html").read_text(encoding="utf-8")
    assert "RNA-seq trust-and-DE cycle report" in html
