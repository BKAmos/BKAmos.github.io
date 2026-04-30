"""FastAPI control plane for the agent-accessible DESeq demo."""
from __future__ import annotations

import json
import base64
import hashlib
import hmac
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
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
ARTIFACT_URL_TTL_SECONDS = int(os.getenv("ARTIFACT_URL_TTL_SECONDS", "3600"))
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


def _has_valid_bearer(authorization: str | None) -> bool:
    return DEMO_MODE or authorization == f"Bearer {API_TOKEN}"


def _job_dir(job_id: str) -> Path:
    return RUNS_DIR / job_id


def _safe_child(root: Path, relative_path: str) -> Path:
    path = (root / relative_path).resolve()
    if root.resolve() not in path.parents and path != root.resolve():
        raise HTTPException(status_code=400, detail="Invalid path")
    return path


def _content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix == ".html":
        return "text/html; charset=utf-8"
    if suffix == ".json":
        return "application/json"
    if suffix == ".csv":
        return "text/csv; charset=utf-8"
    if suffix == ".log":
        return "text/plain; charset=utf-8"
    return "application/octet-stream"


def _artifact_kind(name: str) -> str:
    suffix = Path(name).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        return "image"
    if suffix == ".html":
        return "report"
    if suffix == ".csv":
        return "table"
    if suffix == ".log":
        return "log"
    return "file"


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign_payload(payload: str) -> str:
    signature = hmac.new(API_TOKEN.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).digest()
    return _base64url_encode(signature)


def _make_access_token(job_id: str, artifact_name: str) -> str:
    payload = {
        "job_id": job_id,
        "artifact_name": artifact_name,
        "exp": int(time.time()) + ARTIFACT_URL_TTL_SECONDS,
    }
    encoded = _base64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    return f"{encoded}.{_sign_payload(encoded)}"


def _verify_access_token(token: str | None, job_id: str, artifact_name: str) -> bool:
    if not token or "." not in token:
        return False
    payload_part, signature_part = token.rsplit(".", 1)
    if not hmac.compare_digest(signature_part, _sign_payload(payload_part)):
        return False
    try:
        payload = json.loads(_base64url_decode(payload_part))
    except (ValueError, json.JSONDecodeError):
        return False
    return (
        payload.get("job_id") == job_id
        and payload.get("artifact_name") == artifact_name
        and int(payload.get("exp", 0)) >= int(time.time())
    )


def _require_artifact_access(
    authorization: str | None,
    token: str | None,
    job_id: str,
    artifact_name: str,
) -> None:
    if _has_valid_bearer(authorization) or _verify_access_token(token, job_id, artifact_name):
        return
    raise HTTPException(status_code=401, detail="Missing or invalid artifact access token")


def _read_manifest(job_id: str) -> dict[str, Any]:
    manifest_path = _job_dir(job_id) / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _allowed_artifact_names(job_id: str) -> set[str]:
    manifest = _read_manifest(job_id)
    artifacts = manifest.get("artifacts", [])
    names = {artifact if isinstance(artifact, str) else artifact.get("name") for artifact in artifacts}
    names.discard(None)
    names.add("manifest.json")
    return names


def _artifact_url(job_id: str, artifact_name: str, *, download: bool = False) -> str:
    token = _make_access_token(job_id, artifact_name)
    encoded_name = quote(artifact_name, safe="")
    url = f"/jobs/{job_id}/artifacts/{encoded_name}?token={quote(token, safe='')}"
    if download:
        url += "&download=1"
    return url


def _report_url(job_id: str) -> str:
    token = _make_access_token(job_id, "report.html")
    return f"/jobs/{job_id}/report?token={quote(token, safe='')}"


def _artifact_metadata(job_id: str, artifact_name: str) -> dict[str, str]:
    return {
        "name": artifact_name,
        "kind": _artifact_kind(artifact_name),
        "url": _report_url(job_id) if artifact_name == "report.html" else _artifact_url(job_id, artifact_name),
        "download_url": _artifact_url(job_id, artifact_name, download=True),
        "content_type": _content_type(Path(artifact_name)),
    }


def _with_signed_artifacts(job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("status") != "completed" and payload.get("state") != "completed":
        return payload
    artifacts = payload.get("artifacts") or []
    names = [artifact if isinstance(artifact, str) else artifact.get("name") for artifact in artifacts]
    names = [name for name in names if name]
    enriched = dict(payload)
    enriched["artifacts"] = [_artifact_metadata(job_id, name) for name in names]
    if "report.html" in names:
        enriched["report_url"] = _report_url(job_id)
    return enriched


def _rewrite_report_image_sources(job_id: str, html: str) -> str:
    image_names = {
        name
        for name in _allowed_artifact_names(job_id)
        if Path(name).suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    }

    def replace_src(match: re.Match[str]) -> str:
        prefix, src, suffix = match.groups()
        src_name = Path(src.split("?", 1)[0].split("#", 1)[0]).name
        if src_name not in image_names:
            return match.group(0)
        return f'{prefix}{_artifact_url(job_id, src_name)}{suffix}'

    return re.sub(r'(<img\b[^>]*\bsrc=")([^"]+)(")', replace_src, html)


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
    return _with_signed_artifacts(job_id, {"job_id": job_id, **manifest, "status_url": f"/jobs/{job_id}"})


@app.get("/jobs/{job_id}")
def get_job(job_id: str, _: None = Depends(_auth)) -> dict[str, Any]:
    queued = get_job_payload(job_id) if os.getenv("ENABLE_RQ", "false").lower() == "true" else None
    if queued:
        return _with_signed_artifacts(job_id, queued)
    return _with_signed_artifacts(job_id, _read_manifest(job_id))


@app.get("/jobs/{job_id}/report")
def get_report(
    job_id: str,
    token: str | None = Query(default=None),
    authorization: Annotated[str | None, Header()] = None,
) -> HTMLResponse:
    _require_artifact_access(authorization, token, job_id, "report.html")
    if "report.html" not in _allowed_artifact_names(job_id):
        raise HTTPException(status_code=404, detail="Report not found")
    report_path = _safe_child(_job_dir(job_id), "report.html")
    if not report_path.exists() or report_path.is_dir():
        raise HTTPException(status_code=404, detail="Report not found")
    html = report_path.read_text(encoding="utf-8")
    return HTMLResponse(
        _rewrite_report_image_sources(job_id, html),
        headers={"Cache-Control": "private, max-age=3600"},
    )


@app.get("/jobs/{job_id}/artifacts/{artifact_name}")
def get_artifact(
    job_id: str,
    artifact_name: str,
    token: str | None = Query(default=None),
    download: bool = Query(default=False),
    authorization: Annotated[str | None, Header()] = None,
) -> FileResponse:
    _require_artifact_access(authorization, token, job_id, artifact_name)
    if artifact_name not in _allowed_artifact_names(job_id):
        raise HTTPException(status_code=404, detail="Artifact not found")
    artifact = _safe_child(_job_dir(job_id), artifact_name)
    if not artifact.exists() or artifact.is_dir():
        raise HTTPException(status_code=404, detail="Artifact not found")
    disposition = "attachment" if download else "inline"
    filename = artifact.name.replace('"', "")
    return FileResponse(
        artifact,
        media_type=_content_type(artifact),
        headers={
            "Cache-Control": "private, max-age=3600",
            "Content-Disposition": f'{disposition}; filename="{filename}"',
        },
    )

