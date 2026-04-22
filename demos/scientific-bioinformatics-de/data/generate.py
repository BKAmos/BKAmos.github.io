"""Synthetic log-expression matrix: two conditions, subset of DE genes."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RNG = np.random.default_rng(42)

N_GENES = 400
N_PER_GROUP = 10
DE_GENES = 45
LOG2FC_TRUE = 1.35


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    genes = [f"GENE_{i:04d}" for i in range(N_GENES)]
    de_set = set(RNG.choice(N_GENES, size=DE_GENES, replace=False))

    rows = []
    for gidx, gene in enumerate(genes):
        base = RNG.normal(8.0, 1.2)
        noise_sd = 0.55
        shift = LOG2FC_TRUE if gidx in de_set else 0.0
        for _ in range(N_PER_GROUP):
            rows.append({"gene": gene, "sample": len(rows), "group": "control", "log_expr": base + RNG.normal(0, noise_sd)})
        for _ in range(N_PER_GROUP):
            rows.append(
                {
                    "gene": gene,
                    "sample": len(rows),
                    "group": "treatment",
                    "log_expr": base + shift + RNG.normal(0, noise_sd),
                }
            )

    df = pd.DataFrame(rows)
    df.to_csv(DATA_DIR / "expression_long.csv", index=False)
    print(f"Wrote {DATA_DIR / 'expression_long.csv'}")


if __name__ == "__main__":
    main()
