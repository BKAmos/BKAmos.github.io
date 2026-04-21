"""K-means + PCA visualization and segment profile heatmap."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"

FEATURES = ["annual_spend", "visit_count_annual", "tenure_months"]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATA_DIR / "customers.csv")
    X = df[FEATURES].values
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    km = KMeans(n_clusters=3, random_state=42, n_init=10)
    labels = km.fit_predict(Xs)
    centers_orig = scaler.inverse_transform(km.cluster_centers_)

    pca = PCA(n_components=2, random_state=42)
    xy = pca.fit_transform(Xs)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    scatter = axes[0].scatter(
        xy[:, 0], xy[:, 1], c=labels, cmap="tab10", alpha=0.75, edgecolors="none"
    )
    axes[0].set_title("Customers in PCA space (k-means color)")
    axes[0].set_xlabel("PC1")
    axes[0].set_ylabel("PC2")
    fig.colorbar(scatter, ax=axes[0], label="segment")

    prof = pd.DataFrame(centers_orig, columns=FEATURES)
    prof.index.name = "segment"
    im = axes[1].imshow(prof.T.values, aspect="auto", cmap="viridis")
    axes[1].set_yticks(range(len(FEATURES)), FEATURES)
    axes[1].set_xticks(range(len(prof)), [str(i) for i in prof.index])
    axes[1].set_xlabel("segment (cluster id)")
    axes[1].set_title("Segment centers (original units)")
    fig.colorbar(im, ax=axes[1])
    fig.suptitle("Synthetic customer segmentation", y=1.02)
    fig.tight_layout()
    out = OUT_DIR / "segmentation.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
