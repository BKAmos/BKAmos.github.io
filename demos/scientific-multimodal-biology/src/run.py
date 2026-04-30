"""Canonical correlation between expression+clinical block and imaging block."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cross_decomposition import CCA
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATA_DIR / "samples.csv")
    expr_cols = [c for c in df.columns if c.startswith("expr_")]
    X = df[["age", "sex_male"] + expr_cols].values.astype(float)
    Y = df[["img_texture", "img_size_mm", "img_intensity"]].values.astype(float)

    Xs = StandardScaler().fit_transform(X)
    Ys = StandardScaler().fit_transform(Y)

    cca = CCA(n_components=2)
    Xc, Yc = cca.fit_transform(Xs, Ys)

    out = pd.DataFrame(
        {
            "sample_id": df["sample_id"],
            "group": df["group"],
            "canon_x1": Xc[:, 0],
            "canon_y1": Yc[:, 0],
            "canon_x2": Xc[:, 1],
            "canon_y2": Yc[:, 1],
        }
    )
    out.to_csv(OUT_DIR / "cca_scores.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.25))
    for ax, gx, gy, title in [
        (axes[0], Xc[:, 0], Yc[:, 0], "First canonical pair"),
        (axes[1], Xc[:, 1], Yc[:, 1], "Second canonical pair"),
    ]:
        for g, color, label in [(0, "#4c72b0", "Group 0"), (1, "#c44e52", "Group 1")]:
            m = df["group"].values == g
            ax.scatter(gx[m], gy[m], s=40, alpha=0.75, c=color, label=label)
        ax.set_xlabel("Expression + clinical (canonical)")
        ax.set_ylabel("Imaging features (canonical)")
        ax.set_title(title)
        ax.legend()
        ax.axhline(0, color="#ccc", lw=0.6)
        ax.axvline(0, color="#ccc", lw=0.6)

    fig.suptitle("Multimodal integration — CCA links molecular + clinical to imaging (synthetic)", fontsize=12, y=1.02)
    fig.tight_layout()
    png = OUT_DIR / "cca_scatter.png"
    fig.savefig(png, dpi=120, bbox_inches="tight")
    plt.close(fig)

    # Simple modality correlation summary
    corr = np.corrcoef(Xc[:, 0], Yc[:, 0])[0, 1]
    with open(OUT_DIR / "cca_summary.txt", "w", encoding="utf-8") as f:
        f.write(f"Correlation(canonical axis 1): {corr:.4f}\n")
    print(f"Wrote {png}, {OUT_DIR / 'cca_scores.csv'}")


if __name__ == "__main__":
    main()
