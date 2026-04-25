"""Small Redis/RQ job helpers for the DESeq API."""
from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

import redis
from rq import Queue

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RUNS_DIR = Path(os.getenv("RUNS_DIR", ROOT / "runs"))
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", ROOT / "uploads"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = os.getenv("QUEUE_NAME", "deseq")


def redis_conn() -> redis.Redis:
    return redis.Redis.from_url(REDIS_URL)


def queue() -> Queue:
    return Queue(QUEUE_NAME, connection=redis_conn())


def make_job_id() -> str:
    return f"deseq-{uuid.uuid4().hex[:12]}"


def job_dir(job_id: str) -> Path:
    return RUNS_DIR / job_id


def set_job(job_id: str, data: dict[str, Any]) -> None:
    client = redis_conn()
    current = get_job(job_id) or {}
    current.update(data)
    current["job_id"] = job_id
    client.set(f"job:{job_id}", json.dumps(current, default=str))


def get_job(job_id: str) -> dict[str, Any] | None:
    value = redis_conn().get(f"job:{job_id}")
    if value is None:
        return None
    return json.loads(value)


def get_job_payload(job_id: str) -> dict[str, Any] | None:
    return get_job(job_id)


def update_job_payload(job_id: str, data: dict[str, Any]) -> None:
    set_job(job_id, data)


def enqueue_deseq_job(job_id: str, request_payload: dict[str, Any]) -> None:
    set_job(job_id, {"status": "queued", "request": request_payload, "status_url": f"/jobs/{job_id}"})
    queue().enqueue(
        "queue.worker_loop.run_queued_deseq_job",
        job_id,
        request_payload,
        job_timeout=int(os.getenv("JOB_TIMEOUT_SECONDS", "1800")),
        result_ttl=86400,
        failure_ttl=86400,
    )


def prepare_synthetic_job(job_id: str) -> tuple[Path, Path]:
    dest = job_dir(job_id) / "inputs"
    dest.mkdir(parents=True, exist_ok=True)
    counts = dest / "counts.csv"
    metadata = dest / "metadata.csv"
    shutil.copyfile(DATA_DIR / "counts.csv", counts)
    shutil.copyfile(DATA_DIR / "metadata.csv", metadata)
    return counts, metadata


def artifact_paths(job_id: str) -> list[dict[str, str]]:
    out_dir = job_dir(job_id) / "outputs"
    if not out_dir.exists():
        return []
    artifacts = []
    for path in sorted(out_dir.iterdir()):
        if path.is_file():
            artifacts.append(
                {
                    "name": path.name,
                    "url": f"/jobs/{job_id}/artifacts/{path.name}",
                    "content_type": _content_type(path),
                }
            )
    return artifacts


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
    return "application/octet-stream"
