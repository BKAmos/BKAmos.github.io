"""Regenerate committed portfolio demo outputs (serverless profile)."""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("RUNS_DIR", str(ROOT / "runs"))

from api.main import run_deseq_job  # noqa: E402

if __name__ == "__main__":
    job_id = "portfolio-demo"
    manifest = run_deseq_job(
        job_id,
        {
            "dataset": "synthetic",
            "synthetic_profile": "serverless",
            "condition_column": "condition",
            "reference_level": "control",
            "treatment_level": "treated",
            "batch_column": "batch",
            "min_count": 10,
        },
    )
    job_dir = Path(os.environ["RUNS_DIR"]) / job_id
    out_dir = ROOT / "outputs"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    for name in manifest["artifacts"] + ["manifest.json"]:
        shutil.copy2(job_dir / name, out_dir / name)
    print(
        json.dumps(
            {k: manifest[k] for k in ("job_id", "status", "artifacts", "gene_count", "sample_count")},
            indent=2,
        )
    )
