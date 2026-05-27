"""Render RNA-seq micro-loop cycle reports from orchestrator snapshots."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).resolve().parent


def render_cycle_report(output_dir: Path, cycle_snapshot: dict[str, Any], job_id: str) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("cycle_report.html.j2")
    html = template.render(
        title="RNA-seq trust-and-DE cycle report",
        snapshot=cycle_snapshot,
        job_id=job_id,
    )
    html_path = output_dir / "cycle_report.html"
    json_path = output_dir / "cycle_report.json"
    html_path.write_text(html, encoding="utf-8")
    json_path.write_text(json.dumps(cycle_snapshot, indent=2), encoding="utf-8")
    return {
        "job_id": job_id,
        "status": "completed",
        "artifacts": ["cycle_report.html", "cycle_report.json"],
        "report_path": str(html_path),
    }
