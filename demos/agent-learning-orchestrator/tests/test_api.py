"""API smoke tests with mocked sub-agents."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import api.main as api_main  # noqa: E402
from orchestrator.delegates import SubAgentClient  # noqa: E402


class FakeClient(SubAgentClient):
    def __init__(self) -> None:
        super().__init__(
            contam_base="http://fake",
            deseq_base="http://fake",
            report_base="http://fake",
        )
        self.calls = 0
        self.last_contam: dict[str, str | None] = {}
        self.last_deseq: dict[str, str | None] = {}

    def run_contamination(self, params, *, study_id=None, inputs_dir=None):  # noqa: ANN001, ARG002
        self.last_contam = {"study_id": study_id, "inputs_dir": inputs_dir}
        return {
            "job_id": "contam01",
            "verdict": {"verdict": "no_strong_contamination_signal", "confidence": 0.81},
        }

    def run_deseq(self, params, *, study_id=None, inputs_dir=None):  # noqa: ANN001, ARG002
        self.last_deseq = {"study_id": study_id, "inputs_dir": inputs_dir}
        self.calls += 1
        if self.calls == 1:
            return {"job_id": "deseq01", "top_genes": []}
        genes = [f"GENE_{i}" for i in range(1, 11)]
        return {"job_id": "deseq02", "top_genes": [{"gene_id": g} for g in genes]}

    def run_cycle_report(self, cycle_snapshot):  # noqa: ANN001, ARG002
        return {"job_id": "report01", "status": "completed", "artifacts": ["cycle_report.html"]}


def test_start_component_with_fake_client(monkeypatch, tmp_path):
    studies_dir = tmp_path / "studies"
    monkeypatch.setattr(api_main, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(api_main, "STUDIES_DIR", studies_dir)
    fake = FakeClient()
    monkeypatch.setattr(api_main, "_client", lambda: fake)
    client = TestClient(api_main.app)
    response = client.post(
        "/tools/start_component",
        json={"max_internal_cycles": 2, "deseq": {"min_count": 10, "synthetic_profile": "medium"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "finalized"
    assert fake.last_contam["study_id"]
    assert fake.last_contam["inputs_dir"]
    assert fake.last_deseq["study_id"] == fake.last_contam["study_id"]
    assert fake.last_deseq["inputs_dir"] == fake.last_contam["inputs_dir"]
    assert (studies_dir / fake.last_contam["study_id"] / "study_manifest.json").exists()
    assert body["component_summary"]["parent_handoff"]["recommended_action"] in {
        "proceed_to_downstream",
        "review_design_or_depth",
        "escalate_to_parent",
    }


def test_submit_to_parent_demo_mode_without_webhook(monkeypatch, tmp_path):
    studies_dir = tmp_path / "studies"
    monkeypatch.setattr(api_main, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(api_main, "STUDIES_DIR", studies_dir)
    monkeypatch.setattr(api_main, "PARENT_ORCHESTRATOR_URL", "")
    monkeypatch.setattr(api_main, "_client", lambda: FakeClient())
    client = TestClient(api_main.app)
    start = client.post("/tools/start_component", json={"max_internal_cycles": 2})
    run_id = start.json()["component_run_id"]
    response = client.post("/tools/submit_to_parent", json={"component_run_id": run_id})
    assert response.status_code == 200
    body = response.json()
    assert body["submitted"] is False
    assert body["status"] == "accepted"
    assert body["component_summary"]["component_run_id"] == run_id
