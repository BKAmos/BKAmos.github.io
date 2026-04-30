"""Local runner for the agent-accessible DESeq workflow demo."""
from __future__ import annotations

from pathlib import Path

from worker.run_job import DeseqConfig, run_deseq

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    result = run_deseq(
        DeseqConfig(
            counts_path=ROOT / "data" / "counts.csv",
            metadata_path=ROOT / "data" / "metadata.csv",
            output_dir=ROOT / "outputs",
        )
    )
    print(f"Wrote {len(result['artifacts'])} artifacts to {ROOT / 'outputs'}")
    print("Top gene table: top_genes.csv")


if __name__ == "__main__":
    main()
