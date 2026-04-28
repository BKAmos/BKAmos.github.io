"""Early-fusion multimodal clustering + weekly cluster mix (synthetic support data)."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATA_DIR / "support_records.csv")
    text = (df["subject"].astype(str) + " " + df["body"].astype(str)).values

    text_pipe = Pipeline(
        [
            ("tfidf", TfidfVectorizer(max_features=100, min_df=2, ngram_range=(1, 2))),
            ("svd", TruncatedSVD(n_components=18, random_state=42)),
        ]
    )
    X_text = text_pipe.fit_transform(text)

    tab_enc = ColumnTransformer(
        [
            ("cat", OneHotEncoder(sparse_output=False, handle_unknown="ignore"), ["product_line", "channel"]),
            ("num", StandardScaler(), ["attachment_kb"]),
        ]
    )
    X_tab = tab_enc.fit_transform(df)

    X = np.hstack([X_text, X_tab])
    km = KMeans(n_clusters=4, random_state=42, n_init=10)
    labels = km.fit_predict(X)
    df = df.assign(cluster=labels)

    weekly = (
        df.groupby(["week_index", "cluster"])
        .size()
        .unstack(fill_value=0)
        .sort_index()
    )

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ax0 = axes[0]
    ax0.stackplot(
        weekly.index,
        *[weekly[c] for c in weekly.columns],
        labels=[f"Cluster {c}" for c in weekly.columns],
        alpha=0.88,
    )
    ax0.set_title("Weekly ticket volume by multimodal cluster")
    ax0.set_xlabel("Week index")
    ax0.set_ylabel("Count")
    ax0.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=8)

    xy = X_text[:, :2]
    sc = axes[1].scatter(xy[:, 0], xy[:, 1], c=labels, cmap="tab10", alpha=0.5, s=12, edgecolors="none")
    axes[1].set_title("Text embedding (SVD-1 vs SVD-2), colored by cluster")
    axes[1].set_xlabel("SVD component 1")
    axes[1].set_ylabel("SVD component 2")
    plt.colorbar(sc, ax=axes[1], label="cluster")

    fig.tight_layout()
    out = OUT_DIR / "multimodal_clusters.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
