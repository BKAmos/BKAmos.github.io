from __future__ import annotations

from fastapi.testclient import TestClient

from api import main as api_main


def test_submit_investigation_can_be_retrieved_by_status_endpoint(tmp_path, monkeypatch) -> None:
    runs_dir = tmp_path / "runs"
    monkeypatch.setattr(api_main, "RUNS_DIR", runs_dir)

    client = TestClient(api_main.app)
    response = client.post(
        "/tools/run_investigation",
        json={
            "dataset": "synthetic",
            "profile": "high_contam",
            "sample_count": 6,
            "synthetic_seed": 7,
            "strictness": 0.6,
            "max_iterations": 1,
        },
    )

    assert response.status_code == 200
    submitted = response.json()
    assert submitted["status"] == "completed"
    assert submitted["job_id"]
    assert submitted["status_url"] == f"/jobs/{submitted['job_id']}"
    assert submitted["metrics"]["iterations_completed"] == 1
    assert "verdict.json" in submitted["artifact_names"]

    status_response = client.get(submitted["status_url"])

    assert status_response.status_code == 200
    status = status_response.json()
    assert status["job_id"] == submitted["job_id"]
    assert status["status"] == "completed"
    assert status["verdict"]["iterations_completed"] == 1
    assert any(artifact["name"] == "verdict.json" for artifact in status["artifacts"])
