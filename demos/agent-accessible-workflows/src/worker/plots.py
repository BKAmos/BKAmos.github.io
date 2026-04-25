"""Plot helpers for DESeq workflow artifacts."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


def _safe_neg_log10(values: pd.Series) -> pd.Series:
    clipped = values.clip(lower=np.finfo(float).tiny)
    return -np.log10(clipped)


def volcano_plot(results: pd.DataFrame, out_path: Path) -> None:
    df = results.copy()
    df["padj_plot"] = df["padj"].fillna(1.0)
    df["significant"] = (df["padj_plot"] < 0.05) & (df["log2FoldChange"].abs() >= 1)

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(
        df["log2FoldChange"],
        _safe_neg_log10(df["padj_plot"]),
        c=np.where(df["significant"], "#b23a48", "#6c757d"),
        alpha=0.62,
        s=16,
        edgecolors="none",
    )
    ax.axvline(-1, color="#444", linestyle="--", linewidth=0.8)
    ax.axvline(1, color="#444", linestyle="--", linewidth=0.8)
    ax.axhline(-np.log10(0.05), color="#444", linestyle="--", linewidth=0.8)
    ax.set_title("Differential expression volcano plot")
    ax.set_xlabel("log2 fold change (treated vs control)")
    ax.set_ylabel("-log10 adjusted p-value")
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def ma_plot(results: pd.DataFrame, out_path: Path) -> None:
    df = results.copy()
    df["baseMean_plot"] = df["baseMean"].clip(lower=1)
    df["significant"] = (df["padj"].fillna(1.0) < 0.05) & (df["log2FoldChange"].abs() >= 1)

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(
        np.log10(df["baseMean_plot"]),
        df["log2FoldChange"],
        c=np.where(df["significant"], "#b23a48", "#6c757d"),
        alpha=0.62,
        s=16,
        edgecolors="none",
    )
    ax.axhline(0, color="#444", linestyle="--", linewidth=0.8)
    ax.set_title("MA plot")
    ax.set_xlabel("log10 mean normalized count")
    ax.set_ylabel("log2 fold change")
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def pca_plot(counts: pd.DataFrame, metadata: pd.DataFrame, out_path: Path) -> None:
    log_counts = np.log2(counts.T + 1)
    scaled = StandardScaler().fit_transform(log_counts)
    pca = PCA(n_components=2, random_state=42)
    pcs = pca.fit_transform(scaled)
    explained = pca.explained_variance_ratio_ * 100

    plot_df = metadata.set_index("sample_id").loc[log_counts.index].copy()
    plot_df["PC1"] = pcs[:, 0]
    plot_df["PC2"] = pcs[:, 1]

    colors = {"control": "#1f77b4", "treated": "#d62728"}
    fig, ax = plt.subplots(figsize=(6.5, 5))
    for condition, group in plot_df.groupby("condition"):
        ax.scatter(
            group["PC1"],
            group["PC2"],
            label=condition,
            s=70,
            alpha=0.82,
            color=colors.get(condition, None),
            edgecolors="white",
            linewidth=0.7,
        )
    ax.set_title("Sample PCA on log2 counts")
    ax.set_xlabel(f"PC1 ({explained[0]:.1f}% variance)")
    ax.set_ylabel(f"PC2 ({explained[1]:.1f}% variance)")
    ax.legend(title="Condition")
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def top_genes_heatmap(counts: pd.DataFrame, metadata: pd.DataFrame, results: pd.DataFrame, out_path: Path) -> None:
    ranked = results.dropna(subset=["padj"]).sort_values("padj").head(20)
    selected = ranked.index.intersection(counts.index)
    if selected.empty:
        selected = results.head(20).index.intersection(counts.index)

    heat = np.log2(counts.loc[selected] + 1)
    heat = pd.DataFrame(
        StandardScaler(with_mean=True, with_std=True).fit_transform(heat.T).T,
        index=heat.index,
        columns=heat.columns,
    )
    sample_order = metadata.sort_values(["condition", "batch", "sample_id"])["sample_id"].tolist()
    heat = heat[sample_order]

    fig, ax = plt.subplots(figsize=(9, max(5, 0.28 * len(heat))))
    im = ax.imshow(heat.values, aspect="auto", cmap="RdBu_r", vmin=-2.5, vmax=2.5)
    ax.set_yticks(range(len(heat.index)))
    ax.set_yticklabels(heat.index, fontsize=8)
    ax.set_xticks(range(len(heat.columns)))
    ax.set_xticklabels(heat.columns, rotation=45, ha="right", fontsize=8)
    ax.set_title("Top adjusted-p-value genes (row-scaled log counts)")
    fig.colorbar(im, ax=ax, label="row z-score")
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
