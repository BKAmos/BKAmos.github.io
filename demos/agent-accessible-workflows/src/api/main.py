"""FastAPI control plane for the agent-accessible DESeq demo."""
from __future__ import annotations

import json
import os
import shutil
import sys
import uuid
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from api.jobs import enqueue_deseq_job, get_job_payload, update_job_payload
    from worker.run_job import DeseqConfig, run_deseq
else:
    from .jobs import enqueue_deseq_job, get_job_payload, update_job_payload
    from worker.run_job import DeseqConfig, run_deseq

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RUNS_DIR = Path(os.getenv("RUNS_DIR", ROOT / "runs"))
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", ROOT / "uploads"))
API_TOKEN = os.getenv("API_TOKEN", "dev-token")
DEMO_MODE = os.getenv("DESEQ_DEMO_MODE", "true").lower() == "true"

app = FastAPI(
    title="Agent-accessible DESeq workflow API",
    version="0.1.0",
    description="FastAPI control plane for synthetic and uploaded PyDESeq2 jobs.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DeseqRunRequest(BaseModel):
    dataset: str = Field(default="synthetic", pattern="^(synthetic|uploaded)$")
    counts_uri: str | None = None
    metadata_uri: str | None = None
    counts_url: str | None = None
    metadata_url: str | None = None
    condition_column: str = "condition"
    reference_level: str = "control"
    treatment_level: str = "treated"
    batch_column: str | None = "batch"
    min_count: int = Field(default=10, ge=0)


def _auth(authorization: Annotated[str | None, Header()] = None) -> None:
    if DEMO_MODE:
        return
    expected = f"Bearer {API_TOKEN}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Missing or invalid bearer token")


def _job_dir(job_id: str) -> Path:
    return RUNS_DIR / job_id


def _safe_child(root: Path, relative_path: str) -> Path:
    path = (root / relative_path).resolve()
    if root.resolve() not in path.parents and path != root.resolve():
        raise HTTPException(status_code=400, detail="Invalid path")
    return path


def _resolve_local_uri(uri: str | None, *, default: Path) -> Path:
    if not uri:
        return default
    if uri.startswith("file://"):
        return Path(uri.removeprefix("file://"))
    if uri.startswith("upload://"):
        return _safe_child(UPLOADS_DIR, uri.removeprefix("upload://"))
    return Path(uri)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/synthetic-dataset")
def synthetic_dataset() -> dict[str, Any]:
    return {
        "dataset": "synthetic",
        "counts_uri": f"file://{DATA_DIR / 'counts.csv'}",
        "metadata_uri": f"file://{DATA_DIR / 'metadata.csv'}",
        "counts_url": "/demos/agent-accessible-workflows/data/counts.csv",
        "metadata_url": "/demos/agent-accessible-workflows/data/metadata.csv",
        "sample_count": 12,
        "gene_count": 1000,
        "condition_column": "condition",
        "reference_level": "control",
        "treatment_level": "treated",
        "batch_column": "batch",
    }


@app.post("/uploads")
async def upload_inputs(
    counts: UploadFile = File(...),
    metadata: UploadFile = File(...),
    _: None = Depends(_auth),
) -> dict[str, str]:
    upload_id = uuid.uuid4().hex
    target = UPLOADS_DIR / upload_id
    target.mkdir(parents=True, exist_ok=True)
    counts_path = target / "counts.csv"
    metadata_path = target / "metadata.csv"
    with counts_path.open("wb") as fh:
        shutil.copyfileobj(counts.file, fh)
    with metadata_path.open("wb") as fh:
        shutil.copyfileobj(metadata.file, fh)
    return {
        "upload_id": upload_id,
        "counts_uri": f"upload://{upload_id}/counts.csv",
        "metadata_uri": f"upload://{upload_id}/metadata.csv",
    }


@app.post("/uploads/presign")
def presign_upload(_: None = Depends(_auth)) -> dict[str, Any]:
    upload_id = uuid.uuid4().hex
    return {
        "upload_id": upload_id,
        "mode": "direct-multipart-demo",
        "message": "This local demo accepts POST /uploads multipart files. Production deployments should return signed Object Storage URLs here.",
    }


def run_deseq_job(job_id: str, request_payload: dict[str, Any]) -> dict[str, Any]:
    request = DeseqRunRequest(**request_payload)
    output_dir = _job_dir(job_id)
    counts_path = _resolve_local_uri(request.counts_uri, default=DATA_DIR / "counts.csv")
    metadata_path = _resolve_local_uri(request.metadata_uri, default=DATA_DIR / "metadata.csv")
    manifest = run_deseq(
        DeseqConfig(
            counts_path=counts_path,
            metadata_path=metadata_path,
            output_dir=output_dir,
            condition_column=request.condition_column,
            reference_level=request.reference_level,
            treatment_level=request.treatment_level,
            batch_column=request.batch_column,
            min_count=request.min_count,
            job_id=job_id,
        )
    )
    return manifest


@app.post("/tools/run_deseq")
def submit_deseq(request: DeseqRunRequest, _: None = Depends(_auth)) -> dict[str, Any]:
    job_id = uuid.uuid4().hex[:12]
    if os.getenv("ENABLE_RQ", "false").lower() == "true":
        enqueue_deseq_job(job_id, request.model_dump())
        update_job_payload(job_id, {"job_id": job_id, "status": "queued", "status_url": f"/jobs/{job_id}"})
        return {"job_id": job_id, "status": "queued", "status_url": f"/jobs/{job_id}"}

    try:
        manifest = run_deseq_job(job_id, request.model_dump())
    except Exception as exc:  # pragma: no cover - returned for UI diagnostics.
        job_dir = _job_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "manifest.json").write_text(
            json.dumps({"job_id": job_id, "status": "failed", "message": str(exc)}, indent=2),
            encoding="utf-8",
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job_id": job_id, **manifest, "status_url": f"/jobs/{job_id}"}


@app.get("/jobs/{job_id}")
def get_job(job_id: str, _: None = Depends(_auth)) -> dict[str, Any]:
    queued = get_job_payload(job_id) if os.getenv("ENABLE_RQ", "false").lower() == "true" else None
    if queued:
        return queued
    manifest_path = _job_dir(job_id) / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


@app.get("/jobs/{job_id}/artifacts/{artifact_name}")
def get_artifact(job_id: str, artifact_name: str, _: None = Depends(_auth)) -> FileResponse:
    artifact = _safe_child(_job_dir(job_id), artifact_name)
    if not artifact.exists() or artifact.is_dir():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(artifact)

