"""Per-gene DE stats, Benjamini–Hochberg FDR, volcano plot."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATA_DIR / "expression_long.csv")
    ctrl = df[df["group"] == "control"]
    trt = df[df["group"] == "treatment"]

    records = []
    for gene in df["gene"].unique():
        a = ctrl[ctrl["gene"] == gene]["log_expr"].values
        b = trt[trt["gene"] == gene]["log_expr"].values
        log2fc = float(np.mean(b) - np.mean(a))
        tstat, pval = stats.ttest_ind(b, a, equal_var=False)
        records.append({"gene": gene, "log2fc": log2fc, "pvalue": float(pval), "tstat": float(tstat)})

    res = pd.DataFrame(records)
    _, res["padj"], _, _ = multipletests(res["pvalue"].values, method="fdr_bh")
    res["neg_log10_p"] = -np.log10(np.clip(res["pvalue"], 1e-300, None))
    res.to_csv(OUT_DIR / "de_results.csv", index=False)

    sig = res["padj"] < 0.1
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.scatter(res.loc[~sig, "log2fc"], res.loc[~sig, "neg_log10_p"], s=12, alpha=0.45, c="#888888", label="padj ≥ 0.1")
    ax.scatter(res.loc[sig, "log2fc"], res.loc[sig, "neg_log10_p"], s=18, alpha=0.75, c="#c44e52", label="padj < 0.1")
    ax.axvline(0, color="#333", lw=0.6, alpha=0.5)
    ax.set_xlabel("log2 fold-change (treatment − control)")
    ax.set_ylabel(r"$-\log_{10}(p)$")
    ax.set_title("Toy differential expression — volcano plot (Welch t-test, BH-FDR)")
    ax.legend(loc="upper right", framealpha=0.9)
    fig.tight_layout()
    out = OUT_DIR / "volcano.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"Wrote {out} and {OUT_DIR / 'de_results.csv'}")


if __name__ == "__main__":
    main()
