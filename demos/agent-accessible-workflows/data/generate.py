"""Generate a toy bulk RNA-seq dataset for the DESeq workflow demo.

The synthetic counts intentionally include a small differential-expression
signal so the demo produces visible volcano/MA plots while staying safe to
publish in the repository.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SEED = 42


def main() -> None:
    rng = np.random.default_rng(SEED)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    n_genes = 1000
    n_samples = 12
    n_de = 50

    samples = [f"S{i:02d}" for i in range(1, n_samples + 1)]
    conditions = np.array(["control"] * 6 + ["treated"] * 6)
    batches = np.array(["batch_1", "batch_2"] * 6)

    genes = [f"gene_{i:04d}" for i in range(1, n_genes + 1)]
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
