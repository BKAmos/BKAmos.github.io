"""Synthetic Cα distance matrix for a small protein-like chain."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RNG = np.random.default_rng(42)

N = 72  # residues


def folded_distances(n: int, rng: np.random.Generator) -> np.ndarray:
    """Piecewise-linear chain in 3D with compact globule-like pairwise distances."""
    t = np.linspace(0, 1, n)
    # Helix-like local path + long-range closure
    helix = np.column_stack(
        [
            np.cos(4 * np.pi * t),
            np.sin(4 * np.pi * t),
            0.35 * t,
        ]
    )
    noise = rng.normal(0, 0.08, size=helix.shape)
    coords = helix * (3.8 + 0.4 * np.sin(np.pi * t)[:, None]) + noise
    diff = coords[:, None, :] - coords[None, :, :]
    d = np.sqrt((diff**2).sum(axis=-1))
    return d


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    d = folded_distances(N, RNG)
    # store upper triangle as long format for CSV readability
    i_idx, j_idx = np.triu_indices(N, k=1)
    rows = [{"i": int(i), "j": int(j), "distance_angstrom": round(float(d[i, j]), 3)} for i, j in zip(i_idx, j_idx)]
    pd.DataFrame(rows).to_csv(DATA_DIR / "pairwise_distances.csv", index=False)
    print(f"Wrote {DATA_DIR / 'pairwise_distances.csv'}")


if __name__ == "__main__":
    main()
