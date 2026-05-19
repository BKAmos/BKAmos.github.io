"""Local runner for contamination investigation demo."""
from __future__ import annotations

from pathlib import Path

from worker.run_job import InvestigationConfig, run_investigation

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    result = run_investigation(
        InvestigationConfig(
            alignment_path=ROOT / "data" / "alignment_stats.csv",
            markers_path=ROOT / "data" / "marker_hits.csv",
            taxa_path=ROOT / "data" / "taxa_abundance.csv",
            metrics_path=ROOT / "data" / "sample_metrics.csv",
            qc_log_path=ROOT / "data" / "qc.log",
            output_dir=ROOT / "outputs",
            profile="low_contam",
        )
    )
    print(f"Wrote {len(result['artifacts'])} artifacts to {ROOT / 'outputs'}")
    print(f"Verdict: {result['verdict']['verdict']}")


if __name__ == "__main__":
    main()
