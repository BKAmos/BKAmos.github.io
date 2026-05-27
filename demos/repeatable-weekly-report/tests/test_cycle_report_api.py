"""Smoke tests for the cycle report agent API."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import api.main as report_api  # noqa: E402


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


def test_healthz():
    client = TestClient(report_api.app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_run_cycle_report(monkeypatch, tmp_path):
    monkeypatch.setattr(report_api, "RUNS_DIR", tmp_path)
    client = TestClient(report_api.app)
    response = client.post(
        "/tools/run_cycle_report",
        json={"cycle_snapshot": SAMPLE_SNAPSHOT},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert "cycle_report.html" in body["artifacts"]
    job_id = body["job_id"]

    status = client.get(f"/jobs/{job_id}")
    assert status.status_code == 200
    assert status.json()["status"] == "completed"

    html = client.get(f"/jobs/{job_id}/artifacts/cycle_report.html")
    assert html.status_code == 200
    assert "trust-and-DE" in html.text or "RNA-seq" in html.text
