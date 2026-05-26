"""Shared configuration for AWS serverless DESeq Lambdas."""
from __future__ import annotations

import os

SYNTHETIC_PROFILES: dict[str, dict[str, int]] = {
    "small": {"genes": 1000, "samples": 12, "n_de": 120, "seed": 42},
    "medium": {"genes": 5000, "samples": 24, "n_de": 400, "seed": 84},
    "large": {"genes": 10000, "samples": 32, "n_de": 700, "seed": 126},
    "serverless": {"genes": 100, "samples": 8, "n_de": 20, "seed": 42},
}

SERVERLESS_ARTIFACTS = ("results.csv", "top_genes.csv", "volcano.png", "manifest.json")


def artifact_content_type(name: str) -> str:
    suffix = name.lower().split(".")[-1]
    return {
        "png": "image/png",
        "csv": "text/csv; charset=utf-8",
        "json": "application/json",
    }.get(suffix, "application/octet-stream")


def artifact_content_disposition(name: str) -> str:
    if name.lower().endswith(".png"):
        return f'inline; filename="{name}"'
    return f'attachment; filename="{name}"'


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)
