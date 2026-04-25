"""RQ worker process for queued DESeq jobs."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from redis import Redis
from rq import Queue, Worker

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from api.jobs import QUEUE_NAME  # noqa: E402


def main() -> None:
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    connection = Redis.from_url(redis_url)
    queue = Queue(QUEUE_NAME, connection=connection)
    Worker([queue], connection=connection).work()


if __name__ == "__main__":
    main()
