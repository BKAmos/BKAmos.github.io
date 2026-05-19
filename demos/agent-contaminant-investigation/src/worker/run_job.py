"""Run local contamination investigation workflow."""
from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import duckdb
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"
SRC_DIR = ROOT / "src"
MAX_AGENTIC_ITERATIONS = 3
CONFIDENCE_STOP_THRESHOLD = 0.7
GUARDED_EVIDENCE_QUERIES = (
    "top_non_host_taxa",
    "non_host_ratio_by_sample",
    "unexpected_marker_hits",
    "negative_control_bleed",
    "qc_log_matches",
)
GUARDED_EVIDENCE_TOOLS = (
    "duckdb_table_summaries",
    "marker_hit_checks",
    "negative_control_checks",
    "qc_log_matching",
    "top_non_host_taxa",
)


@dataclass(frozen=True)
class InvestigationConfig:
    alignment_path: Path = DATA_DIR / "alignment_stats.csv"
    markers_path: Path = DATA_DIR / "marker_hits.csv"
    taxa_path: Path = DATA_DIR / "taxa_abundance.csv"
    metrics_path: Path = DATA_DIR / "sample_metrics.csv"
    qc_log_path: Path = DATA_DIR / "qc.log"
    output_dir: Path = OUT_DIR
    profile: str = "low_contam"
    strictness: float = 0.6
    max_iterations: int = 2
    job_id: str = "sample-job"

    def __post_init__(self) -> None:
        try:
            max_iterations = int(self.max_iterations)
        except (TypeError, ValueError) as exc:
            raise ValueError("max_iterations must be an integer between 1 and 3") from exc
        if not 1 <= max_iterations <= MAX_AGENTIC_ITERATIONS:
            raise ValueError("max_iterations must be between 1 and 3")
        object.__setattr__(self, "max_iterations", max_iterations)


def _write_report(output_dir: Path, manifest: dict[str, Any]) -> None:
    env = Environment(
        loader=FileSystemLoader(SRC_DIR),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("report.html.j2")
    rendered = template.render(
        title="Contamination Investigation Report",
        summary_note="Synthetic-only agentic triage output.",
        metrics=manifest["metrics"],
        top_genes_table=pd.DataFrame(manifest["signals"]).to_html(index=False, classes="top-genes"),
        config=manifest["config"],
        plot_context={},
        top_genes=manifest["signals"],
        condition_counts={},
    )
    (output_dir / "report.html").write_text(rendered, encoding="utf-8")


def _plot_top_taxa(top_taxa: list[dict[str, Any]], output_path: Path) -> None:
    taxa = [row["taxon"] for row in top_taxa[:8]]
    values = [float(row["total_reads"]) for row in top_taxa[:8]]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(taxa, values)
    ax.set_xlabel("Read count")
    ax.set_title("Top non-host taxa")
    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _build_investigator_plan(
    *,
    config: InvestigationConfig,
    iteration: int,
    previous_verdict: str | None,
) -> dict[str, Any]:
    return {
        "iteration": iteration,
        "selected_queries": list(GUARDED_EVIDENCE_QUERIES),
        "allowed_evidence_tools": list(GUARDED_EVIDENCE_TOOLS),
        "evidence_guardrails": [
            "DuckDB table summaries only",
            "Marker-hit checks only from marker_hits.csv",
            "Negative-control checks only from sample_metrics.csv",
            "QC log matching only against known warning patterns",
            "Top non-host taxa only from taxa_abundance.csv",
        ],
        "grep": {"file": "qc.log", "keywords": "warn|marker_hits=[3-9]|contam_reads=[2-9][0-9]{3,}"},
        "review_focus": (
            "initial_screen"
            if iteration == 1
            else "recheck_uncertain_signals_against_controls_and_qc_log"
        ),
        "previous_verdict": previous_verdict,
        "max_iterations": int(config.max_iterations),
    }


def _collect_guarded_evidence(
    con: duckdb.DuckDBPyConnection,
    config: InvestigationConfig,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    top_taxa = con.execute(
        """
        SELECT taxon, SUM(read_count) AS total_reads
        FROM taxa_abundance
        WHERE domain = 'non_host'
        GROUP BY taxon
        ORDER BY total_reads DESC
        LIMIT 8
        """
    ).fetchdf().to_dict("records")
    non_host_ratios = con.execute(
        """
        SELECT sample_id, ROUND(1.0 * non_host_reads / NULLIF(total_reads, 0), 5) AS non_host_ratio
        FROM alignment_stats
        ORDER BY non_host_ratio DESC
        """
    ).fetchdf().to_dict("records")
    markers = con.execute(
        """
        SELECT sample_id, marker_name, hit_count
        FROM marker_hits
        WHERE hit_count > 0
        ORDER BY hit_count DESC, sample_id
        LIMIT 20
        """
    ).fetchdf().to_dict("records")
    control_bleed = con.execute(
        """
        SELECT sample_id, contaminant_reads
        FROM sample_metrics
        WHERE is_negative_control = true
        ORDER BY contaminant_reads DESC
        """
    ).fetchdf().to_dict("records")

    grep_hits: list[str] = []
    for line in config.qc_log_path.read_text(encoding="utf-8").splitlines():
        if "qc=warn" in line or "marker_hits=3" in line or "marker_hits=4" in line:
            grep_hits.append(line)
    grep_hits = grep_hits[:20]

    evidence = {
        "top_non_host_taxa": top_taxa,
        "non_host_ratio_by_sample": non_host_ratios[:12],
        "unexpected_marker_hits": markers[:12],
        "negative_control_bleed": control_bleed,
        "grep_hits": grep_hits,
    }
    return top_taxa, evidence


def _score_evidence(evidence: dict[str, Any], strictness: float) -> dict[str, Any]:
    non_host_ratios = evidence["non_host_ratio_by_sample"]
    markers = evidence["unexpected_marker_hits"]
    control_bleed = evidence["negative_control_bleed"]
    max_ratio = max((float(row["non_host_ratio"]) for row in non_host_ratios), default=0.0)
    max_marker = max((int(row["hit_count"]) for row in markers), default=0)
    max_control = max((int(row["contaminant_reads"]) for row in control_bleed), default=0)
    risk_score = (max_ratio * 45.0) + (max_marker * 10.0) + (max_control / 220.0)
    strict_gate = 42.0 + (1.0 - float(strictness)) * 18.0
    confidence = min(0.99, max(0.1, risk_score / 100.0))
    if risk_score >= strict_gate:
        verdict = "contaminant_likely"
    elif risk_score < 18:
        verdict = "no_strong_contamination_signal"
    else:
        verdict = "uncertain"
    return {
        "max_ratio": max_ratio,
        "max_marker": max_marker,
        "max_control": max_control,
        "risk_score": risk_score,
        "confidence": confidence,
        "verdict": verdict,
    }


def _build_summary(score: dict[str, Any]) -> dict[str, Any]:
    verdict = score["verdict"]
    if verdict == "contaminant_likely":
        executive_summary = (
            "Investigation found elevated non-host reads and marker evidence consistent with "
            "possible foreign genetic material."
        )
    elif verdict == "uncertain":
        executive_summary = "Evidence remained inconclusive under current strictness settings."
    else:
        executive_summary = "Evidence did not cross contamination threshold under current strictness settings."
    return {
        "executive_summary": executive_summary,
        "signals": [
            {"name": "max_non_host_ratio", "value": round(score["max_ratio"], 5)},
            {"name": "max_marker_hits", "value": score["max_marker"]},
            {"name": "max_negative_control_contaminant_reads", "value": score["max_control"]},
            {"name": "risk_score", "value": round(score["risk_score"], 3)},
        ],
        "confidence": round(score["confidence"], 3),
    }


def _build_verdict_payload(score: dict[str, Any]) -> dict[str, Any]:
    return {
        "verdict": score["verdict"],
        "confidence": round(score["confidence"], 3),
        "requires_reiteration": False,
        "recommended_next_steps": [
            "Re-sequence highest-risk samples with deeper host depletion.",
            "Inspect negative controls for prep contamination trends.",
            "Validate top contaminant taxa via orthogonal assay (qPCR).",
        ],
    }


def run_investigation(config: InvestigationConfig) -> dict[str, Any]:
    output_dir = Path(config.output_dir)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(config.alignment_path, output_dir / "alignment_stats.csv")
    shutil.copyfile(config.markers_path, output_dir / "marker_hits.csv")
    shutil.copyfile(config.taxa_path, output_dir / "taxa_abundance.csv")
    shutil.copyfile(config.metrics_path, output_dir / "sample_metrics.csv")
    shutil.copyfile(config.qc_log_path, output_dir / "qc.log")

    con = duckdb.connect()
    con.execute("CREATE TABLE alignment_stats AS SELECT * FROM read_csv_auto(?)", [str(config.alignment_path)])
    con.execute("CREATE TABLE marker_hits AS SELECT * FROM read_csv_auto(?)", [str(config.markers_path)])
    con.execute("CREATE TABLE taxa_abundance AS SELECT * FROM read_csv_auto(?)", [str(config.taxa_path)])
    con.execute("CREATE TABLE sample_metrics AS SELECT * FROM read_csv_auto(?)", [str(config.metrics_path)])

    overview = con.execute(
        """
        SELECT
          COUNT(*) AS sample_count,
          AVG(1.0 * non_host_reads / NULLIF(total_reads, 0)) AS mean_non_host_ratio,
          SUM(CASE WHEN is_negative_control THEN 1 ELSE 0 END) AS negative_controls
        FROM alignment_stats
        """
    ).fetchdf().to_dict("records")[0]

    iterations: list[dict[str, Any]] = []
    previous_verdict: str | None = None
    stop_reason = "iteration_cap"
    top_taxa: list[dict[str, Any]] = []
    for iteration in range(1, config.max_iterations + 1):
        investigator_plan = _build_investigator_plan(
            config=config,
            iteration=iteration,
            previous_verdict=previous_verdict,
        )
        top_taxa, evidence = _collect_guarded_evidence(con, config)
        score = _score_evidence(evidence, config.strictness)
        summary = _build_summary(score)
        verdict_payload = _build_verdict_payload(score)
        verdict_payload["stable_with_previous"] = previous_verdict == verdict_payload["verdict"]
        iteration_payload = {
            "iteration": iteration,
            "plan": investigator_plan,
            "evidence": evidence,
            "summary": summary,
            "verdict": verdict_payload,
        }
        iterations.append(iteration_payload)

        if verdict_payload["verdict"] != "uncertain":
            stop_reason = "final_verdict"
            break
        if verdict_payload["confidence"] >= CONFIDENCE_STOP_THRESHOLD:
            stop_reason = "confidence_threshold"
            break
        if previous_verdict == verdict_payload["verdict"]:
            stop_reason = "stable_verdict"
            break
        previous_verdict = verdict_payload["verdict"]

    final_iteration = iterations[-1]
    investigator_plan = final_iteration["plan"]
    evidence = final_iteration["evidence"]
    summary = final_iteration["summary"]
    verdict_payload = final_iteration["verdict"]
    verdict_payload.update(
        {
            "iterations_completed": len(iterations),
            "stop_reason": stop_reason,
            "requires_reiteration": len(iterations) > 1
            or (verdict_payload["verdict"] == "uncertain" and stop_reason == "iteration_cap"),
        }
    )

    _plot_top_taxa(top_taxa, output_dir / "top_non_host_taxa.png")
    for name, payload in (
        ("overview.json", overview),
        ("investigator_plan.json", investigator_plan),
        ("evidence.json", evidence),
        ("summary.json", summary),
        ("verdict.json", verdict_payload),
    ):
        (output_dir / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    timeline = [{"stage": "overview", "status": "ok", "iteration": 0}]
    for item in iterations:
        timeline.extend(
            [
                {"stage": "investigator", "status": "ok", "iteration": item["iteration"]},
                {"stage": "executor", "status": "ok", "iteration": item["iteration"]},
                {"stage": "summary", "status": "ok", "iteration": item["iteration"]},
                {
                    "stage": "verdict_review",
                    "status": "ok",
                    "iteration": item["iteration"],
                    "verdict": item["verdict"]["verdict"],
                    "confidence": item["verdict"]["confidence"],
                },
            ]
        )
    timeline.append({"stage": "final_verdict", "status": "ok", "stop_reason": stop_reason})
    (output_dir / "timeline.json").write_text(json.dumps(timeline, indent=2), encoding="utf-8")

    artifacts = [
        "alignment_stats.csv",
        "marker_hits.csv",
        "taxa_abundance.csv",
        "sample_metrics.csv",
        "qc.log",
        "overview.json",
        "investigator_plan.json",
        "evidence.json",
        "summary.json",
        "verdict.json",
        "timeline.json",
        "top_non_host_taxa.png",
        "report.html",
    ]
    manifest = {
        "job_id": config.job_id,
        "status": "completed",
        "analysis": "agentic contamination investigation",
        "config": {k: str(v) if isinstance(v, Path) else v for k, v in asdict(config).items()},
        "metrics": {
            "sample_count": int(overview["sample_count"]),
            "mean_non_host_ratio": round(float(overview["mean_non_host_ratio"]), 5),
            "negative_controls": int(overview["negative_controls"]),
            "risk_score": summary["signals"][3]["value"],
            "iterations_completed": len(iterations),
        },
        "signals": summary["signals"],
        "artifacts": artifacts,
        "summary": summary,
        "verdict": verdict_payload,
        "iterations": iterations,
    }
    _write_report(output_dir, manifest)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    manifest = run_investigation(InvestigationConfig())
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
