"""Generate a toy bulk RNA-seq dataset for the DESeq workflow demo.

The synthetic counts intentionally include a small differential-expression
signal so the demo produces visible volcano/MA plots while staying safe to
publish in the repository.

Larger stress tests (local only; do not commit huge CSVs to git):

  python data/generate.py --genes 20000 --samples 48 --n-de 800

Then rebuild API/worker images so Docker copies the new matrices:

  cd src && docker compose build --no-cache api worker && docker compose up -d
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
from worker.synthetic import write_synthetic_dataset  # noqa: E402

DATA_DIR = ROOT / "data"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--genes", type=int, default=1000, help="Number of genes (rows). Default: 1000")
    p.add_argument(
        "--samples",
        type=int,
        default=12,
        help="Number of samples (columns); split half control / half treated. Default: 12",
    )
    p.add_argument(
        "--n-de",
        type=int,
        default=None,
        metavar="N",
        help="How many genes are truly DE (default: max(50, genes//20))",
    )
    p.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    try:
        counts_path, metadata_path, truth_path = write_synthetic_dataset(
            output_dir=DATA_DIR,
            genes=args.genes,
            samples=args.samples,
            n_de=args.n_de,
            seed=args.seed,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    print(f"Wrote {counts_path}")
    print(f"Wrote {metadata_path}")
    print(f"Wrote {truth_path}")


if __name__ == "__main__":
    main()
