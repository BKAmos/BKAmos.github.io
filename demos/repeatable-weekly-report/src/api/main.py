"""FastAPI surface for cycle report generation."""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from typing_extensions import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

_SRC_DIR = Path(__file__).resolve().parents[1]
if __package__ in {None, "", "api"}:
    if str(_SRC_DIR) not in sys.path:
        sys.path.insert(0, str(_SRC_DIR))
    from run_cycle_report import render_cycle_report
else:
    from ..run_cycle_report import render_cycle_report

ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = Path(os.getenv("RUNS_DIR", ROOT / "runs"))
API_TOKEN = os.getenv("API_TOKEN", "dev-token")
DEMO_MODE = os.getenv("REPORT_DEMO_MODE", "true").lower() == "true"

app = FastAPI(title="Cycle report agent API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CycleReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cycle_snapshot: Dict[str, Any] = Field(default_factory=dict)


def _auth(authorization: Annotated[Optional[str], Header()] = None) -> None:
    if DEMO_MODE:
        return
    if authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Missing or invalid bearer token")


def _job_dir(job_id: str) -> Path:
    return RUNS_DIR / job_id


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/tools/run_cycle_report")
def run_cycle_report(request: CycleReportRequest, _: None = Depends(_auth)) -> Dict[str, Any]:
    job_id = uuid.uuid4().hex[:12]
    output_dir = _job_dir(job_id)
    manifest = render_cycle_report(output_dir, request.cycle_snapshot, job_id)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"job_id": job_id, "status_url": f"/jobs/{job_id}", **manifest}


@app.get("/jobs/{job_id}")
def get_job(job_id: str, _: None = Depends(_auth)) -> Dict[str, Any]:
    manifest_path = _job_dir(job_id) / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


@app.get("/jobs/{job_id}/artifacts/{artifact_name}")
def get_artifact(job_id: str, artifact_name: str, _: None = Depends(_auth)) -> FileResponse:
    if artifact_name not in {"cycle_report.html", "cycle_report.json", "manifest.json"}:
        raise HTTPException(status_code=404, detail="Artifact not found")
    path = _job_dir(job_id) / artifact_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    media = "text/html" if artifact_name.endswith(".html") else "application/json"
    return FileResponse(path, media_type=media)
