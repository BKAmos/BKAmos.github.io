"""RQ worker process for queued DESeq jobs."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from redis import Redis
from rq import Queue, Worker

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from api.jobs import QUEUE_NAME  # noqa: E402


def run_queued_deseq_job(job_id: str, request_payload: dict) -> str:
    """RQ entrypoint: run PyDESeq2 for one job and publish status + manifest to Redis."""
    from api.jobs import update_job_payload

    import api.main as api_main  # import after fork; avoids pulling FastAPI until job runs

    update_job_payload(job_id, {"job_id": job_id, "status": "running"})
    try:
        manifest = api_main.run_deseq_job(job_id, request_payload)
        out = {
            **manifest,
            "job_id": job_id,
            "status": "completed",
            "status_url": f"/jobs/{job_id}",
        }
        update_job_payload(job_id, out)
        return job_id
    except Exception as exc:  # pragma: no cover
        msg = str(exc)
        job_dir = api_main._job_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "manifest.json").write_text(
            json.dumps({"job_id": job_id, "status": "failed", "message": msg}, indent=2),
            encoding="utf-8",
        )
        update_job_payload(job_id, {"job_id": job_id, "status": "failed", "message": msg})
        raise


def main() -> None:
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    connection = Redis.from_url(redis_url)
    queue = Queue(QUEUE_NAME, connection=connection)
    Worker([queue], connection=connection).work()


if __name__ == "__main__":
    main()
