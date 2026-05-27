"""Verify contamination API accepts pre-built study inputs."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
ORCH_ROOT = ROOT.parent / "agent-learning-orchestrator"
sys.path.insert(0, str(ORCH_ROOT / "src"))
sys.path.insert(0, str(ROOT / "src"))

from api import main as api_main  # noqa: E402
from orchestrator.study_bundle import write_study_bundle  # noqa: E402


def test_run_investigation_with_shared_inputs_dir(tmp_path, monkeypatch) -> None:
    runs_dir = tmp_path / "runs"
    monkeypatch.setattr(api_main, "RUNS_DIR", runs_dir)

    study_dir = tmp_path / "studies" / "study01"
    write_study_bundle(
        study_dir,
        study_id="study01",
        contam_profile="high_contam",
        deseq_profile="medium",
        cohort_seed=7,
    )

    client = TestClient(api_main.app)
    response = client.post(
        "/tools/run_investigation",
        json={
            "dataset": "study",
            "study_id": "study01",
            "inputs_dir": str(study_dir),
            "profile": "high_contam",
            "sample_count": 24,
            "synthetic_seed": 7,
            "strictness": 0.6,
            "max_iterations": 1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["dataset"] == "study"
    assert body["study_id"] == "study01"
    assert body["inputs_dir"] == str(study_dir.resolve())
    assert body["status"] == "completed"
