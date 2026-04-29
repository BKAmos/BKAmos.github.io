"""FastAPI control plane for the agent-accessible DESeq demo."""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from api.jobs import enqueue_deseq_job, get_job_payload
    from worker.run_job import DeseqConfig, run_deseq
    from worker.synthetic import write_synthetic_dataset
else:
    from .jobs import enqueue_deseq_job, get_job_payload
    from worker.run_job import DeseqConfig, run_deseq
    from worker.synthetic import write_synthetic_dataset

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RUNS_DIR = Path(os.getenv("RUNS_DIR", ROOT / "runs"))
API_TOKEN = os.getenv("API_TOKEN", "dev-token")
DEMO_MODE = os.getenv("DESEQ_DEMO_MODE", "true").lower() == "true"
SYNTHETIC_PROFILES: dict[str, dict[str, int]] = {
    "small": {"genes": 1000, "samples": 12, "n_de": 120, "seed": 42},
    "medium": {"genes": 5000, "samples": 24, "n_de": 400, "seed": 84},
    "large": {"genes": 10000, "samples": 32, "n_de": 700, "seed": 126},
}

app = FastAPI(
    title="Agent-accessible DESeq workflow API",
    version="0.1.0",
    description="FastAPI control plane for synthetic-only PyDESeq2 jobs.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DeseqRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset: str = Field(default="synthetic", pattern="^synthetic$")
    synthetic_profile: str = Field(default="medium", pattern="^(small|medium|large)$")
    synthetic_seed: int | None = Field(default=None, ge=0, le=2_147_483_647)
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


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "agent-accessible-deseq-api",
        "docs": "/docs",
        "health": "/healthz",
    }


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
        "profiles": SYNTHETIC_PROFILES,
    }

def run_deseq_job(job_id: str, request_payload: dict[str, Any]) -> dict[str, Any]:
    request = DeseqRunRequest(**request_payload)
    output_dir = _job_dir(job_id)
    profile = SYNTHETIC_PROFILES[request.synthetic_profile].copy()
    if request.synthetic_seed is not None:
        profile["seed"] = request.synthetic_seed
    # Keep generated inputs outside output_dir because run_deseq() recreates output_dir.
    inputs_dir = RUNS_DIR / "_synthetic_inputs" / job_id
    counts_path, metadata_path, _truth_path = write_synthetic_dataset(
        output_dir=inputs_dir,
        genes=profile["genes"],
        samples=profile["samples"],
        n_de=profile["n_de"],
        seed=profile["seed"],
    )
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
    manifest["dataset"] = "synthetic"
    manifest["synthetic_profile"] = request.synthetic_profile
    manifest["synthetic_request"] = profile
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


@app.post("/tools/run_deseq")
def submit_deseq(request: DeseqRunRequest, _: None = Depends(_auth)) -> dict[str, Any]:
    job_id = uuid.uuid4().hex[:12]
    if os.getenv("ENABLE_RQ", "false").lower() == "true":
        enqueue_deseq_job(job_id, request.model_dump())
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

