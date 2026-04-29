"""Shared synthetic RNA-seq dataset generation helpers."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def generate_synthetic_data(
    *,
    genes: int,
    samples: int,
    n_de: int | None = None,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if genes < 50:
        raise ValueError("Need at least 50 genes for a meaningful fit.")
    if samples < 4 or samples % 2 != 0:
        raise ValueError("samples must be an even number >= 4 (balanced control/treated).")

    rng = np.random.default_rng(seed)
    n_de_genes = n_de if n_de is not None else max(50, genes // 20)
    n_de_genes = min(n_de_genes, genes)

    width = max(2, len(str(samples)))
    sample_ids = [f"S{i:0{width}d}" for i in range(1, samples + 1)]
    half = samples // 2
    conditions = np.array(["control"] * half + ["treated"] * half)
    batches = np.array([f"batch_{(i % 2) + 1}" for i in range(samples)])

    gene_width = max(4, len(str(genes)))
    gene_ids = [f"gene_{i:0{gene_width}d}" for i in range(1, genes + 1)]
    base_means = rng.lognormal(mean=4.2, sigma=1.0, size=genes)
    dispersions = rng.gamma(shape=2.0, scale=0.22, size=genes) + 0.05

    log2_fc = np.zeros(genes)
    de_idx = rng.choice(genes, size=n_de_genes, replace=False)
    log2_fc[de_idx] = rng.choice([-1, 1], size=n_de_genes) * rng.uniform(1.2, 2.2, size=n_de_genes)

    sample_size_factors = rng.lognormal(mean=0.0, sigma=0.18, size=samples)
    counts = np.zeros((genes, samples), dtype=int)

    for sample_idx, condition in enumerate(conditions):
        fold_change = np.where(condition == "treated", np.power(2.0, log2_fc), 1.0)
        mu = base_means * fold_change * sample_size_factors[sample_idx]

        # Gamma-Poisson mixture parameterization for negative-binomial-like counts.
        shape = 1.0 / dispersions
        scale = mu * dispersions
        rates = rng.gamma(shape=shape, scale=scale)
        counts[:, sample_idx] = rng.poisson(rates)

    counts_df = pd.DataFrame(counts, index=gene_ids, columns=sample_ids)
    metadata_df = pd.DataFrame(
        {
            "sample_id": sample_ids,
            "condition": conditions,
            "batch": batches,
        }
    )
    truth_df = pd.DataFrame(
        {
            "gene_id": gene_ids,
            "true_log2_fold_change": log2_fc,
            "is_differential": np.isin(np.arange(genes), de_idx),
        }
    )
    return counts_df, metadata_df, truth_df


def write_synthetic_dataset(
    *,
    output_dir: Path,
    genes: int,
    samples: int,
    n_de: int | None = None,
    seed: int = 42,
) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    counts_df, metadata_df, truth_df = generate_synthetic_data(
        genes=genes,
        samples=samples,
        n_de=n_de,
        seed=seed,
    )
    counts_path = output_dir / "counts.csv"
    metadata_path = output_dir / "metadata.csv"
    truth_path = output_dir / "truth.csv"
    counts_df.to_csv(counts_path)
    metadata_df.to_csv(metadata_path, index=False)
    truth_df.to_csv(truth_path, index=False)
    return counts_path, metadata_path, truth_path
