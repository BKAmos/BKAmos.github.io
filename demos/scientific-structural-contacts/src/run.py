"""Rebuild distance matrix, binary contact map at 8 Å."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"

THRESHOLD_A = 8.0


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    edges = pd.read_csv(DATA_DIR / "pairwise_distances.csv")
    n = int(max(edges["i"].max(), edges["j"].max())) + 1
    d = np.zeros((n, n))
    np.fill_diagonal(d, 0.0)
    for _, row in edges.iterrows():
        i, j, dist = int(row["i"]), int(row["j"]), row["distance_angstrom"]
        d[i, j] = d[j, i] = dist

    contacts = (d > 0) & (d <= THRESHOLD_A)
    np.fill_diagonal(contacts, False)
    # exclude |i-j| < 2 (sequential neighbors)
    for i in range(n):
        for j in range(max(0, i - 1), min(n, i + 2)):
            contacts[i, j] = False

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.25))
    im0 = axes[0].imshow(d, cmap="magma", aspect="auto")
    axes[0].set_title("Synthetic Cα distances (Å)")
    axes[0].set_xlabel("Residue j")
    axes[0].set_ylabel("Residue i")
    plt.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

    im1 = axes[1].imshow(contacts.astype(float), cmap="Greys", vmin=0, vmax=1, aspect="auto")
    axes[1].set_title(f"Contact map (≤ {THRESHOLD_A:g} Å, |i−j| ≥ 2)")
    axes[1].set_xlabel("Residue j")
    axes[1].set_ylabel("Residue i")
    plt.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

    fig.suptitle("Structural biology toy — pairwise distances from a compact chain", fontsize=12, y=1.02)
    fig.tight_layout()
    out = OUT_DIR / "contact_map.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
