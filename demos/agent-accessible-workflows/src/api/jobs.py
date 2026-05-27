"""Small Redis/RQ job helpers for the DESeq API."""
from __future__ import annotations

import json
import os
from typing import Any

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = os.getenv("QUEUE_NAME", "deseq")


def redis_conn() -> Any:
    import redis

    return redis.Redis.from_url(REDIS_URL)


def queue() -> Any:
    from rq import Queue

    return Queue(QUEUE_NAME, connection=redis_conn())


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
        "jobqueue.worker_loop.run_queued_deseq_job",
        job_id,
        request_payload,
        job_timeout=int(os.getenv("JOB_TIMEOUT_SECONDS", "1800")),
        result_ttl=86400,
        failure_ttl=86400,
    )
