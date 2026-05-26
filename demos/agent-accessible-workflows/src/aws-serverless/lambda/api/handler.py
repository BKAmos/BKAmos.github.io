"""API Gateway HTTP API handler: healthz, submit job, get job status."""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3

from shared.config import SYNTHETIC_PROFILES, artifact_content_type

TABLE_NAME = os.environ["JOBS_TABLE_NAME"]
BUCKET_NAME = os.environ["ARTIFACTS_BUCKET_NAME"]
WORKER_FUNCTION_NAME = os.environ["WORKER_FUNCTION_NAME"]
API_TOKEN = os.environ["API_TOKEN"]
PRESIGN_TTL = int(os.environ.get("ARTIFACT_URL_TTL_SECONDS", "3600"))
JOB_TTL_DAYS = int(os.environ.get("JOB_TTL_DAYS", "7"))
CORS_ALLOW_ORIGIN = os.environ.get("CORS_ALLOW_ORIGIN", "*")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)
s3 = boto3.client("s3")
lambda_client = boto3.client("lambda")


def _response(status: int, body: dict[str, Any] | list[Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": CORS_ALLOW_ORIGIN,
            "Access-Control-Allow-Headers": "authorization,content-type",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        },
        "body": json.dumps(body),
    }


def _auth(headers: dict[str, str]) -> bool:
    expected = f"Bearer {API_TOKEN}"
    auth = headers.get("authorization") or headers.get("Authorization", "")
    return auth == expected


def _ttl_epoch() -> int:
    return int((datetime.now(timezone.utc) + timedelta(days=JOB_TTL_DAYS)).timestamp())


def _artifact_kind(name: str) -> str:
    if name.endswith(".png"):
        return "image"
    if name.endswith(".csv"):
        return "table"
    if name.endswith(".json"):
        return "file"
    return "file"


def _presign(key: str) -> tuple[str, str]:
    # Plain get_object only — ResponseContentDisposition in presigned URLs triggers
    # "Request specific response headers cannot be used for anonymous GET requests".
    # Content-Type/Disposition are set on upload in the worker Lambda.
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET_NAME, "Key": key},
        ExpiresIn=PRESIGN_TTL,
    )
    return url, url


def _enrich_artifacts(job_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
    names = manifest.get("artifacts") or []
    enriched = []
    for name in names:
        key = f"runs/{job_id}/{name}"
        url, download_url = _presign(key)
        enriched.append(
            {
                "name": name,
                "kind": _artifact_kind(name),
                "url": url,
                "download_url": download_url,
                "content_type": artifact_content_type(name),
            }
        )
    payload = dict(manifest)
    payload["artifacts"] = enriched
    return payload


def _validate_request(body: dict[str, Any]) -> dict[str, Any]:
    if body.get("dataset", "synthetic") != "synthetic":
        raise ValueError("Only synthetic dataset is supported")
    profile = body.get("synthetic_profile", "serverless")
    if profile not in SYNTHETIC_PROFILES:
        raise ValueError(f"Invalid synthetic_profile: {profile}")
    if profile != "serverless":
        profile = "serverless"
    return {
        "dataset": "synthetic",
        "synthetic_profile": profile,
        "synthetic_seed": body.get("synthetic_seed"),
        "condition_column": body.get("condition_column", "condition"),
        "reference_level": body.get("reference_level", "control"),
        "treatment_level": body.get("treatment_level", "treated"),
        "batch_column": None,
        "min_count": int(body.get("min_count", 10)),
    }


def _submit(body: dict[str, Any]) -> dict[str, Any]:
    request = _validate_request(body)
    job_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    table.put_item(
        Item={
            "job_id": job_id,
            "status": "queued",
            "request": request,
            "created_at": now,
            "updated_at": now,
            "expires_at": _ttl_epoch(),
        }
    )
    lambda_client.invoke(
        FunctionName=WORKER_FUNCTION_NAME,
        InvocationType="Event",
        Payload=json.dumps({"job_id": job_id, "request": request}).encode("utf-8"),
    )
    return {"job_id": job_id, "status": "queued", "status_url": f"/jobs/{job_id}"}


def _get_job(job_id: str) -> dict[str, Any]:
    item = table.get_item(Key={"job_id": job_id}).get("Item")
    if not item:
        return _response(404, {"detail": "Job not found"})
    status = item.get("status", "unknown")
    if status in {"queued", "running"}:
        return _response(
            200,
            {
                "job_id": job_id,
                "status": status,
                "message": item.get("message", ""),
            },
        )
    if status == "failed":
        return _response(
            200,
            {
                "job_id": job_id,
                "status": "failed",
                "message": item.get("error", "Job failed"),
            },
        )
    manifest = json.loads(item.get("manifest_json", "{}"))
    manifest["job_id"] = job_id
    manifest["status"] = "completed"
    return _response(200, _enrich_artifacts(job_id, manifest))


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    method = event.get("requestContext", {}).get("http", {}).get("method", event.get("httpMethod", "GET"))
    path = event.get("rawPath") or event.get("path", "/")
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}

    if method == "OPTIONS":
        return _response(200, {"status": "ok"})

    if path.endswith("/healthz") and method == "GET":
        return _response(200, {"status": "ok"})

    job_id = (event.get("pathParameters") or {}).get("job_id")
    if not job_id and re.fullmatch(r"/jobs/[0-9a-f]{12}", path):
        job_id = path.rsplit("/", 1)[-1]
    if method == "GET" and job_id and re.fullmatch(r"[0-9a-f]{12}", job_id):
        if not _auth(headers):
            return _response(401, {"detail": "Missing or invalid bearer token"})
        return _get_job(job_id)

    if method == "POST" and path.endswith("/tools/run_deseq"):
        if not _auth(headers):
            return _response(401, {"detail": "Missing or invalid bearer token"})
        try:
            body = json.loads(event.get("body") or "{}")
        except json.JSONDecodeError:
            return _response(400, {"detail": "Invalid JSON body"})
        try:
            return _response(200, _submit(body))
        except ValueError as exc:
            return _response(400, {"detail": str(exc)})

    return _response(404, {"detail": "Not found"})
