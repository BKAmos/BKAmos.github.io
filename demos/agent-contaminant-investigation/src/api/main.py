"""FastAPI control plane for contamination investigation demo."""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Union
from typing_extensions import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

if __package__ in {None, "", "api"}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from api.jobs import enqueue_job, get_job_payload
    from api.storage import get_stored_artifact, safe_artifact_name, upload_artifacts
    from worker.run_job import InvestigationConfig, run_investigation
    from worker.synthetic import PROFILES, write_synthetic_dataset
else:
    from .jobs import enqueue_job, get_job_payload
    from .storage import get_stored_artifact, safe_artifact_name, upload_artifacts
    from worker.run_job import InvestigationConfig, run_investigation
    from worker.synthetic import PROFILES, write_synthetic_dataset

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RUNS_DIR = Path(os.getenv("RUNS_DIR", ROOT / "runs"))
API_TOKEN = os.getenv("API_TOKEN", "dev-token")
DEMO_MODE = os.getenv("CONTAM_DEMO_MODE", os.getenv("DESEQ_DEMO_MODE", "true")).lower() == "true"

app = FastAPI(title="Contamination Investigation API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InvestigationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset: str = Field(default="synthetic", pattern="^(synthetic|study)$")
    profile: str = Field(default="low_contam", pattern="^(clean|low_contam|high_contam|edge_case)$")
    sample_count: int = Field(default=24, ge=6, le=128)
    synthetic_seed: int = Field(default=42, ge=0, le=2_147_483_647)
    strictness: float = Field(default=0.6, ge=0.1, le=1.0)
    max_iterations: int = Field(default=2, ge=1, le=3)
    study_id: Optional[str] = None
    inputs_dir: Optional[str] = None


STUDY_INPUT_FILES = (
    "alignment_stats.csv",
    "marker_hits.csv",
    "taxa_abundance.csv",
    "sample_metrics.csv",
    "qc.log",
)


def _resolve_study_inputs(request: InvestigationRequest) -> Path | None:
    if not request.inputs_dir:
        return None
    path = Path(request.inputs_dir).resolve()
    if not path.is_dir():
        raise ValueError(f"inputs_dir not found: {path}")
    for name in STUDY_INPUT_FILES:
        if not (path / name).exists():
            raise ValueError(f"Missing {name} in inputs_dir")
    return path


def _auth(authorization: Annotated[Optional[str], Header()] = None) -> None:
    if DEMO_MODE:
        return
    if authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Missing or invalid bearer token")


def _auth_or_token(
    authorization: Annotated[Optional[str], Header()] = None,
    token: Optional[str] = None,
) -> None:
    if DEMO_MODE:
        return
    if authorization == f"Bearer {API_TOKEN}" or token == API_TOKEN:
        return
    raise HTTPException(status_code=401, detail="Missing or invalid bearer token")


def _job_dir(job_id: str) -> Path:
    return RUNS_DIR / job_id


def _read_manifest(job_id: str) -> Dict[str, Any]:
    path = _job_dir(job_id) / "manifest.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    return json.loads(path.read_text(encoding="utf-8"))


def run_investigation_job(job_id: str, request_payload: Dict[str, Any]) -> Dict[str, Any]:
    request = InvestigationRequest(**request_payload)
    output_dir = _job_dir(job_id)
    shared_inputs = _resolve_study_inputs(request)
    if shared_inputs:
        paths = {
            "alignment_stats": shared_inputs / "alignment_stats.csv",
            "marker_hits": shared_inputs / "marker_hits.csv",
            "taxa_abundance": shared_inputs / "taxa_abundance.csv",
            "sample_metrics": shared_inputs / "sample_metrics.csv",
            "qc_log": shared_inputs / "qc.log",
        }
    else:
        inputs_dir = RUNS_DIR / "_synthetic_inputs" / job_id
        paths = write_synthetic_dataset(
            output_dir=inputs_dir,
            sample_count=request.sample_count,
            profile=request.profile,
            seed=request.synthetic_seed,
        )
    manifest = run_investigation(
        InvestigationConfig(
            alignment_path=paths["alignment_stats"],
            markers_path=paths["marker_hits"],
            taxa_path=paths["taxa_abundance"],
            metrics_path=paths["sample_metrics"],
            qc_log_path=paths["qc_log"],
            output_dir=output_dir,
            profile=request.profile,
            strictness=request.strictness,
            max_iterations=request.max_iterations,
            job_id=job_id,
        )
    )
    artifact_names = [str(name) for name in manifest.get("artifacts", [])]
    artifact_records = upload_artifacts(job_id, output_dir, artifact_names)
    manifest["dataset"] = request.dataset
    manifest["profile"] = request.profile
    manifest["sample_count"] = request.sample_count
    if request.study_id:
        manifest["study_id"] = request.study_id
    if shared_inputs:
        manifest["inputs_dir"] = str(shared_inputs)
    manifest["artifact_names"] = artifact_names
    manifest["artifacts"] = artifact_records
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/synthetic-dataset")
def synthetic_dataset() -> Dict[str, Any]:
    return {"dataset": "synthetic", "profiles": PROFILES}


@app.post("/tools/run_investigation")
def submit_investigation(request: InvestigationRequest, _: None = Depends(_auth)) -> Dict[str, Any]:
    job_id = uuid.uuid4().hex[:12]
    if os.getenv("ENABLE_RQ", "false").lower() == "true":
        enqueue_job(job_id, request.model_dump())
        return {"job_id": job_id, "status": "queued", "status_url": f"/jobs/{job_id}"}
    try:
        manifest = run_investigation_job(job_id, request.model_dump())
    except Exception as exc:
        out = _job_dir(job_id)
        out.mkdir(parents=True, exist_ok=True)
        (out / "manifest.json").write_text(
            json.dumps({"job_id": job_id, "status": "failed", "message": str(exc)}, indent=2),
            encoding="utf-8",
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job_id": job_id, "status_url": f"/jobs/{job_id}", **manifest}


@app.get("/jobs/{job_id}")
def get_job(job_id: str, _: None = Depends(_auth)) -> Dict[str, Any]:
    queued = get_job_payload(job_id) if os.getenv("ENABLE_RQ", "false").lower() == "true" else None
    return queued or _read_manifest(job_id)


@app.get("/jobs/{job_id}/artifacts/{artifact_name}", response_model=None)
def get_artifact(
    job_id: str,
    artifact_name: str,
    _: None = Depends(_auth_or_token),
    token: Optional[str] = Query(default=None),
) -> Union[FileResponse, StreamingResponse]:
    try:
        safe_name = safe_artifact_name(artifact_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    stored = get_stored_artifact(job_id, safe_name)
    if stored is not None:
        return StreamingResponse(stored["body"], media_type=stored["content_type"])

    path = (_job_dir(job_id) / safe_name).resolve()
    if not path.exists() or path.is_dir():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(path)

