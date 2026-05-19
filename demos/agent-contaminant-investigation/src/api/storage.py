"""Artifact storage helpers for the contamination investigation API."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterator

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

ARTIFACT_STORAGE = os.getenv("ARTIFACT_STORAGE", "filesystem").lower()
MINIO_ENDPOINT_URL = os.getenv("MINIO_ENDPOINT_URL", "http://minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", os.getenv("MINIO_ROOT_USER", "deseqdemo"))
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", os.getenv("MINIO_ROOT_PASSWORD", "deseqdemopassword"))
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "contamination-artifacts")
MINIO_REGION = os.getenv("MINIO_REGION", "us-east-1")


def storage_enabled() -> bool:
    return ARTIFACT_STORAGE == "minio"


def content_type(path_or_name: Path | str) -> str:
    suffix = Path(path_or_name).suffix.lower()
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


def safe_artifact_name(artifact_name: str) -> str:
    name = Path(artifact_name).name
    if name != artifact_name or name in {"", ".", ".."}:
        raise ValueError("Invalid artifact name")
    return name


def artifact_key(job_id: str, artifact_name: str) -> str:
    return f"runs/{job_id}/{safe_artifact_name(artifact_name)}"


def _client() -> BaseClient:
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT_URL,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name=MINIO_REGION,
    )


def ensure_bucket(client: BaseClient | None = None) -> None:
    if not storage_enabled():
        return
    s3 = client or _client()
    try:
        s3.head_bucket(Bucket=MINIO_BUCKET)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code not in {"404", "NoSuchBucket", "NotFound"}:
            raise
        try:
            s3.create_bucket(Bucket=MINIO_BUCKET)
        except ClientError as create_exc:
            create_code = create_exc.response.get("Error", {}).get("Code", "")
            if create_code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
                raise


def upload_artifacts(job_id: str, output_dir: Path, artifact_names: list[str]) -> list[dict[str, Any]]:
    """Upload completed artifacts when MinIO is enabled and return API-facing metadata."""
    records: list[dict[str, Any]] = []
    s3 = _client() if storage_enabled() else None
    if s3 is not None:
        ensure_bucket(s3)

    for artifact_name in artifact_names:
        safe_name = safe_artifact_name(artifact_name)
        path = output_dir / safe_name
        if not path.is_file():
            continue

        record: dict[str, Any] = {
            "name": safe_name,
            "url": f"/jobs/{job_id}/artifacts/{safe_name}",
            "content_type": content_type(path),
            "storage": "minio" if s3 is not None else "filesystem",
        }
        if s3 is not None:
            key = artifact_key(job_id, safe_name)
            s3.upload_file(
                str(path),
                MINIO_BUCKET,
                key,
                ExtraArgs={"ContentType": record["content_type"]},
            )
            record.update({"bucket": MINIO_BUCKET, "key": key})
        records.append(record)
    return records


def get_stored_artifact(job_id: str, artifact_name: str) -> dict[str, Any] | None:
    if not storage_enabled():
        return None
    safe_name = safe_artifact_name(artifact_name)
    s3 = _client()
    try:
        response = s3.get_object(Bucket=MINIO_BUCKET, Key=artifact_key(job_id, safe_name))
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in {"404", "NoSuchKey", "NoSuchBucket", "NotFound"}:
            return None
        raise
    return {
        "body": _iter_body(response["Body"]),
        "content_type": response.get("ContentType") or content_type(safe_name),
    }


def _iter_body(body: Any) -> Iterator[bytes]:
    try:
        while chunk := body.read(1024 * 1024):
            yield chunk
    finally:
        body.close()
