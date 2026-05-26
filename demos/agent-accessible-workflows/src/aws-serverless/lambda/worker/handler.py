"""Async worker: synthetic data → PyDESeq2 (serverless profile) → S3 + DynamoDB."""
from __future__ import annotations

import os

# Lambda sets JOBLIB_MULTIPROCESSING=0, which unregisters joblib's loky backend.
# PyDESeq2 then falls back to threading and fails on inner_max_num_threads.
os.environ.pop("JOBLIB_MULTIPROCESSING", None)

import json
import shutil
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3

# Worker image copies repo src/ to /var/task/src
sys.path.insert(0, "/var/task/src")

from shared.config import (  # noqa: E402
    SERVERLESS_ARTIFACTS,
    SYNTHETIC_PROFILES,
    artifact_content_disposition,
    artifact_content_type,
)
from worker.run_job import DeseqConfig, run_deseq  # noqa: E402
from worker.synthetic import write_synthetic_dataset  # noqa: E402

TABLE_NAME = os.environ["JOBS_TABLE_NAME"]
BUCKET_NAME = os.environ["ARTIFACTS_BUCKET_NAME"]
JOB_TTL_DAYS = int(os.environ.get("JOB_TTL_DAYS", "7"))

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)
s3 = boto3.client("s3")


def _ttl_epoch() -> int:
    from datetime import timedelta

    return int((datetime.now(timezone.utc) + timedelta(days=JOB_TTL_DAYS)).timestamp())


def _update(job_id: str, **fields: Any) -> None:
    # Use ExpressionAttributeNames — DynamoDB reserves words like "status".
    expr_names: dict[str, str] = {"#updated_at": "updated_at"}
    expr_values: dict[str, Any] = {":updated_at": datetime.now(timezone.utc).isoformat()}
    set_parts = ["#updated_at = :updated_at"]
    for key, value in fields.items():
        name_key = f"#{key}"
        expr_names[name_key] = key
        expr_values[f":{key}"] = value
        set_parts.append(f"{name_key} = :{key}")
    table.update_item(
        Key={"job_id": job_id},
        UpdateExpression="SET " + ", ".join(set_parts),
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
    )


def _upload_artifacts(job_id: str, output_dir: Path) -> None:
    prefix = f"runs/{job_id}/"
    for name in SERVERLESS_ARTIFACTS:
        path = output_dir / name
        if not path.exists():
            continue
        s3.upload_file(
            str(path),
            BUCKET_NAME,
            prefix + name,
            ExtraArgs={
                "ContentType": artifact_content_type(name),
                "ContentDisposition": artifact_content_disposition(name),
            },
        )


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    job_id = event["job_id"]
    request = event["request"]
    _update(job_id, status="running")

    tmp_root = Path(f"/tmp/deseq-{job_id}")
    output_dir = tmp_root / "output"
    inputs_dir = tmp_root / "inputs"

    try:
        profile_name = request.get("synthetic_profile", "serverless")
        profile = SYNTHETIC_PROFILES[profile_name].copy()
        if request.get("synthetic_seed") is not None:
            profile["seed"] = int(request["synthetic_seed"])

        counts_path, metadata_path, _ = write_synthetic_dataset(
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
                condition_column=request.get("condition_column", "condition"),
                reference_level=request.get("reference_level", "control"),
                treatment_level=request.get("treatment_level", "treated"),
                batch_column=None,
                min_count=int(request.get("min_count", 10)),
                n_cpus=1,
                job_id=job_id,
                artifact_profile="serverless",
            )
        )
        manifest["dataset"] = "synthetic"
        manifest["synthetic_profile"] = profile_name
        manifest["synthetic_request"] = profile
        (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        _upload_artifacts(job_id, output_dir)
        _update(
            job_id,
            status="completed",
            manifest_json=json.dumps(manifest),
            expires_at=_ttl_epoch(),
        )
        return {"job_id": job_id, "status": "completed"}
    except Exception as exc:  # pragma: no cover
        _update(job_id, status="failed", error=str(exc), expires_at=_ttl_epoch())
        print(traceback.format_exc())
        raise
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
