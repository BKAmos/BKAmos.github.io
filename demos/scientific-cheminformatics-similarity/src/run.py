"""Tanimoto similarity to query, PCA of fingerprints, scatter colored by cluster."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"


def fp_to_array(s: str) -> np.ndarray:
    return np.array([int(c) for c in s], dtype=np.uint8)


def tanimoto(a: np.ndarray, b: np.ndarray) -> float:
    inter = int((a & b).sum())
    union = int((a | b).sum())
    return inter / union if union else 0.0


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATA_DIR / "compounds.csv")
    fps = np.stack([fp_to_array(s) for s in df["fingerprint"]])
    query = fps[0]

    sims = [tanimoto(query, fps[i]) for i in range(len(df))]
    df = df.assign(tanimoto_to_query=np.round(sims, 4))
    df.sort_values("tanimoto_to_query", ascending=False).to_csv(OUT_DIR / "similarity_ranked.csv", index=False)

    X = fps.astype(float)
    xy = PCA(n_components=2, random_state=42).fit_transform(X)
    plot_df = df.assign(pc1=xy[:, 0], pc2=xy[:, 1])

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.25))
    colors = ["#4c72b0", "#55a868", "#c44e52"]
    for ax, hue, title in [
        (axes[0], plot_df["cluster"], "PCA of binary fingerprints (by synthetic scaffold)"),
        (axes[1], plot_df["tanimoto_to_query"], "Same embedding colored by Tanimoto to CMP-000"),
    ]:
        if ax is axes[0]:
            for k in sorted(plot_df["cluster"].unique()):
                sub = plot_df[plot_df["cluster"] == k]
                ax.scatter(sub["pc1"], sub["pc2"], s=22, alpha=0.75, c=colors[k % len(colors)], label=f"Scaffold {k}")
            ax.legend(title="Cluster", fontsize=8)
        else:
            sc = ax.scatter(plot_df["pc1"], plot_df["pc2"], s=28, alpha=0.85, c=plot_df["tanimoto_to_query"], cmap="viridis")
            plt.colorbar(sc, ax=ax, label="Tanimoto")
        ax.set_xlabel("PC1")
        ax.set_ylabel("PC2")
        ax.set_title(title)

    fig.suptitle("Cheminformatics-style landscape (synthetic fingerprints, no RDKit)", fontsize=12, y=1.02)
    fig.tight_layout()
    out = OUT_DIR / "pca_landscape.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out} and {OUT_DIR / 'similarity_ranked.csv'}")


if __name__ == "__main__":
    main()
