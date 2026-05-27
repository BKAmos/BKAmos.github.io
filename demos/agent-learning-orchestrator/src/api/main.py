"""FastAPI control plane for the RNA-seq trust-and-DE micro-loop component."""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from typing_extensions import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

if __package__ in {None, "", "api"}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from orchestrator.delegates import SubAgentClient
    from orchestrator.runner import load_run, run_component_loop, save_run
    from orchestrator.state import COMPONENT_ID, ContamParams, DeseqParams, ComponentRun
else:
    from ..orchestrator.delegates import SubAgentClient
    from ..orchestrator.runner import load_run, run_component_loop, save_run
    from ..orchestrator.state import COMPONENT_ID, ContamParams, DeseqParams, ComponentRun

ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = Path(os.getenv("RUNS_DIR", ROOT / "runs"))
STUDIES_DIR = Path(os.getenv("STUDIES_DIR", ROOT.parent / "_shared_studies"))
API_TOKEN = os.getenv("API_TOKEN", "dev-token")
DEMO_MODE = os.getenv("ORCHESTRATOR_DEMO_MODE", "true").lower() == "true"

CONTAM_API_BASE = os.getenv("CONTAM_API_BASE", "http://127.0.0.1:8001")
DESEQ_API_BASE = os.getenv("DESEQ_API_BASE", "http://127.0.0.1:8000")
REPORT_API_BASE = os.getenv("REPORT_API_BASE", "http://127.0.0.1:8002")
PARENT_ORCHESTRATOR_URL = os.getenv("PARENT_ORCHESTRATOR_URL", "")

app = FastAPI(
    title="RNA-seq trust-and-DE component orchestrator",
    version="0.1.0",
    description="Minimal learning loop: contamination QC → DESeq → report → reflect.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ContamParamsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile: str = Field(default="low_contam", pattern="^(clean|low_contam|high_contam|edge_case)$")
    sample_count: int = Field(default=24, ge=6, le=128)
    synthetic_seed: int = Field(default=42, ge=0, le=2_147_483_647)
    strictness: float = Field(default=0.6, ge=0.1, le=1.0)
    max_iterations: int = Field(default=2, ge=1, le=3)


class DeseqParamsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    synthetic_profile: str = Field(default="medium", pattern="^(small|medium|large)$")
    synthetic_seed: Optional[int] = Field(default=None, ge=0, le=2_147_483_647)
    condition_column: str = "condition"
    reference_level: str = "control"
    treatment_level: str = "treated"
    batch_column: Optional[str] = "batch"
    min_count: int = Field(default=10, ge=0)


class StartComponentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_internal_cycles: int = Field(default=3, ge=1, le=3)
    contamination: ContamParamsModel = Field(default_factory=ContamParamsModel)
    deseq: DeseqParamsModel = Field(default_factory=DeseqParamsModel)


class SubmitToParentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    component_run_id: str = Field(min_length=1)
    parent_url: Optional[str] = None


def _auth(authorization: Annotated[Optional[str], Header()] = None) -> None:
    if DEMO_MODE:
        return
    if authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Missing or invalid bearer token")


def _run_dir(component_run_id: str) -> Path:
    return RUNS_DIR / component_run_id


def _client() -> SubAgentClient:
    return SubAgentClient(
        contam_base=CONTAM_API_BASE,
        deseq_base=DESEQ_API_BASE,
        report_base=REPORT_API_BASE,
        api_token=API_TOKEN if not DEMO_MODE else "",
    )


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/component-info")
def component_info() -> Dict[str, Any]:
    return {
        "component_id": COMPONENT_ID,
        "description": "Trust before expression micro-loop with internal reflect/adapt.",
        "sub_agents": {
            "contamination": CONTAM_API_BASE,
            "deseq": DESEQ_API_BASE,
            "report": REPORT_API_BASE,
        },
    }


@app.post("/tools/start_component")
def start_component(request: StartComponentRequest, _: None = Depends(_auth)) -> Dict[str, Any]:
    component_run_id = uuid.uuid4().hex[:12]
    run = ComponentRun(
        component_run_id=component_run_id,
        max_internal_cycles=request.max_internal_cycles,
        contam_params=ContamParams(**request.contamination.model_dump()),
        deseq_params=DeseqParams(**request.deseq.model_dump()),
    )
    run = run_component_loop(_client(), run, studies_dir=STUDIES_DIR)
    save_run(_run_dir(component_run_id), run)
    return {
        "component_run_id": component_run_id,
        "status": run.status,
        "phase": run.phase,
        "summary_url": f"/components/{component_run_id}/summary",
        "status_url": f"/components/{component_run_id}",
        "component_summary": run.component_summary,
        "message": run.message,
    }


@app.get("/components/{component_run_id}")
def get_component_status(component_run_id: str, _: None = Depends(_auth)) -> Dict[str, Any]:
    try:
        return load_run(_run_dir(component_run_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Component run not found") from exc


@app.get("/components/{component_run_id}/summary")
def get_component_summary(component_run_id: str, _: None = Depends(_auth)) -> Dict[str, Any]:
    try:
        payload = load_run(_run_dir(component_run_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Component run not found") from exc
    summary = payload.get("component_summary")
    if not summary:
        raise HTTPException(status_code=404, detail="Component summary not ready")
    return summary


@app.post("/tools/submit_to_parent")
def submit_to_parent(request: SubmitToParentRequest, _: None = Depends(_auth)) -> Dict[str, Any]:
    """POST finalized component_summary.json to a parent orchestrator webhook."""
    try:
        payload = load_run(_run_dir(request.component_run_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Component run not found") from exc
    summary = payload.get("component_summary")
    if not summary:
        raise HTTPException(status_code=404, detail="Component summary not ready")
    parent_url = (request.parent_url or PARENT_ORCHESTRATOR_URL or "").strip()
    if not parent_url:
        if DEMO_MODE:
            return {
                "status": "accepted",
                "submitted": False,
                "component_run_id": request.component_run_id,
                "message": "No PARENT_ORCHESTRATOR_URL configured; summary returned for local demo.",
                "component_summary": summary,
            }
        raise HTTPException(
            status_code=400,
            detail="Set PARENT_ORCHESTRATOR_URL or pass parent_url in the request body.",
        )
    headers = {"Content-Type": "application/json"}
    if not DEMO_MODE:
        headers["Authorization"] = f"Bearer {API_TOKEN}"
    try:
        response = httpx.post(parent_url, json=summary, headers=headers, timeout=30.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Parent orchestrator rejected handoff: {exc}") from exc
    return {
        "status": "submitted",
        "submitted": True,
        "component_run_id": request.component_run_id,
        "parent_url": parent_url,
        "parent_status_code": response.status_code,
    }
