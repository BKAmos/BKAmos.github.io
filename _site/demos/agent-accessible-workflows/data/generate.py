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

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
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
    rng = np.random.default_rng(args.seed)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    n_genes = args.genes
    n_samples = args.samples
    if n_genes < 50:
        raise SystemExit("Need at least --genes 50 for a meaningful fit.")
    if n_samples < 4 or n_samples % 2 != 0:
        raise SystemExit("--samples must be an even number >= 4 (balanced control/treated).")

    n_de = args.n_de if args.n_de is not None else max(50, n_genes // 20)
    n_de = min(n_de, n_genes)

    width = max(2, len(str(n_samples)))
    samples = [f"S{i:0{width}d}" for i in range(1, n_samples + 1)]
    half = n_samples // 2
    conditions = np.array(["control"] * half + ["treated"] * half)
    batches = np.array([f"batch_{(i % 2) + 1}" for i in range(n_samples)])

    gene_width = max(4, len(str(n_genes)))
    genes = [f"gene_{i:0{gene_width}d}" for i in range(1, n_genes + 1)]
    base_means = rng.lognormal(mean=4.2, sigma=1.0, size=n_genes)
    dispersions = rng.gamma(shape=2.0, scale=0.22, size=n_genes) + 0.05

    log2_fc = np.zeros(n_genes)
    de_idx = rng.choice(n_genes, size=n_de, replace=False)
    log2_fc[de_idx] = rng.choice([-1, 1], size=n_de) * rng.uniform(1.2, 2.2, size=n_de)

    sample_size_factors = rng.lognormal(mean=0.0, sigma=0.18, size=n_samples)
    counts = np.zeros((n_genes, n_samples), dtype=int)

    for sample_idx, condition in enumerate(conditions):
        fold_change = np.where(condition == "treated", np.power(2.0, log2_fc), 1.0)
        mu = base_means * fold_change * sample_size_factors[sample_idx]

        # Gamma-Poisson mixture parameterization for negative-binomial-like counts.
        shape = 1.0 / dispersions
        scale = mu * dispersions
        rates = rng.gamma(shape=shape, scale=scale)
        counts[:, sample_idx] = rng.poisson(rates)

    counts_df = pd.DataFrame(counts, index=genes, columns=samples)
    metadata_df = pd.DataFrame(
        {
            "sample_id": samples,
            "condition": conditions,
            "batch": batches,
        }
    )
    truth_df = pd.DataFrame(
        {
            "gene_id": genes,
            "true_log2_fold_change": log2_fc,
            "is_differential": np.isin(np.arange(n_genes), de_idx),
        }
    )

    counts_df.to_csv(DATA_DIR / "counts.csv")
    metadata_df.to_csv(DATA_DIR / "metadata.csv", index=False)
    truth_df.to_csv(DATA_DIR / "truth.csv", index=False)
    print(f"Wrote {DATA_DIR / 'counts.csv'}")
    print(f"Wrote {DATA_DIR / 'metadata.csv'}")
    print(f"Wrote {DATA_DIR / 'truth.csv'}")


if __name__ == "__main__":
    main()
