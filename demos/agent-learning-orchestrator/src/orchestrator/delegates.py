"""HTTP delegates for sub-agent APIs."""
from __future__ import annotations

import time
from typing import Any

import httpx

from orchestrator.state import ContamParams, DeseqParams


class SubAgentError(RuntimeError):
    pass


class SubAgentClient:
    def __init__(
        self,
        *,
        contam_base: str,
        deseq_base: str,
        report_base: str,
        api_token: str = "",
        poll_interval: float = 0.5,
        poll_timeout: float = 300.0,
    ) -> None:
        self.contam_base = contam_base.rstrip("/")
        self.deseq_base = deseq_base.rstrip("/")
        self.report_base = report_base.rstrip("/")
        self.api_token = api_token
        self.poll_interval = poll_interval
        self.poll_timeout = poll_timeout

    def _headers(self) -> dict[str, str]:
        if not self.api_token:
            return {}
        return {"Authorization": f"Bearer {self.api_token}"}

    def _post(self, base: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(f"{base}{path}", json=payload, headers=self._headers())
        if response.status_code >= 400:
            raise SubAgentError(f"{path} failed: {response.status_code} {response.text}")
        return response.json()

    def _get(self, base: str, path: str) -> dict[str, Any]:
        with httpx.Client(timeout=60.0) as client:
            response = client.get(f"{base}{path}", headers=self._headers())
        if response.status_code >= 400:
            raise SubAgentError(f"{path} failed: {response.status_code} {response.text}")
        return response.json()

    def _wait_for_job(self, base: str, job_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + self.poll_timeout
        while time.monotonic() < deadline:
            payload = self._get(base, f"/jobs/{job_id}")
            status = payload.get("status") or payload.get("state")
            if status in {"completed", "failed"}:
                if status == "failed":
                    raise SubAgentError(payload.get("message") or f"Job {job_id} failed")
                return payload
            if status not in {"queued", "running", "pending", None} and payload.get("verdict"):
                return payload
            time.sleep(self.poll_interval)
        raise SubAgentError(f"Timed out waiting for job {job_id}")

    def run_contamination(self, params: ContamParams, *, study_id: str | None = None, inputs_dir: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "dataset": "study" if inputs_dir else "synthetic",
            "profile": params.profile,
            "sample_count": params.sample_count,
            "synthetic_seed": params.synthetic_seed,
            "strictness": params.strictness,
            "max_iterations": params.max_iterations,
        }
        if study_id:
            payload["study_id"] = study_id
        if inputs_dir:
            payload["inputs_dir"] = inputs_dir
        submitted = self._post(
            self.contam_base,
            "/tools/run_investigation",
            payload,
        )
        job_id = submitted["job_id"]
        if submitted.get("status") == "queued":
            return self._wait_for_job(self.contam_base, job_id)
        return submitted

    def run_deseq(self, params: DeseqParams, *, study_id: str | None = None, inputs_dir: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "dataset": "study" if inputs_dir else "synthetic",
            "synthetic_profile": params.synthetic_profile,
            "condition_column": params.condition_column,
            "reference_level": params.reference_level,
            "treatment_level": params.treatment_level,
            "batch_column": params.batch_column,
            "min_count": params.min_count,
        }
        if params.synthetic_seed is not None:
            payload["synthetic_seed"] = params.synthetic_seed
        if study_id:
            payload["study_id"] = study_id
        if inputs_dir:
            payload["inputs_dir"] = inputs_dir
        submitted = self._post(self.deseq_base, "/tools/run_deseq", payload)
        job_id = submitted["job_id"]
        if submitted.get("status") == "queued":
            return self._wait_for_job(self.deseq_base, job_id)
        return submitted

    def run_cycle_report(self, cycle_snapshot: dict[str, Any]) -> dict[str, Any]:
        submitted = self._post(
            self.report_base,
            "/tools/run_cycle_report",
            {"cycle_snapshot": cycle_snapshot},
        )
        job_id = submitted["job_id"]
        if submitted.get("status") == "queued":
            return self._wait_for_job(self.report_base, job_id)
        return submitted
