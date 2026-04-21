"""Welch t-test, CI for mean difference, summary figure."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATA_DIR / "experiment.csv")
    c = df.loc[df["arm"] == "control", "metric"]
    t = df.loc[df["arm"] == "treatment", "metric"]
    res = stats.ttest_ind(t, c, equal_var=False)
    diff = t.mean() - c.mean()
    se = np.sqrt(t.var(ddof=1) / len(t) + c.var(ddof=1) / len(c))
    df_welch = (se**4) / (
        (t.var(ddof=1) ** 2) / ((len(t) ** 2) * (len(t) - 1))
        + (c.var(ddof=1) ** 2) / ((len(c) ** 2) * (len(c) - 1))
    )
    crit = stats.t.ppf(0.975, df_welch)
    ci_low = diff - crit * se
    ci_high = diff + crit * se

    fig, axes = plt.subplots(1, 2, figsize=(9, 3.5))
    axes[0].hist(c, bins=30, alpha=0.7, label="Control", color="#157878")
    axes[0].hist(t, bins=30, alpha=0.7, label="Treatment", color="#c44e52")
    axes[0].set_title("Metric distribution by arm")
    axes[0].legend()
    axes[1].axis("off")
    lines = [
        f"n: control={len(c)}, treatment={len(t)}",
        f"Mean control: {c.mean():.2f} · Mean treatment: {t.mean():.2f}",
        f"Difference (T−C): {diff:+.2f}",
        f"95% CI for difference: [{ci_low:+.2f}, {ci_high:+.2f}]",
        f"Welch t-statistic: {res.statistic:.2f}, p-value: {res.pvalue:.4g}",
        "",
        "Decision hint: if 95% CI excludes 0 in the favorable direction,",
        "there is conventional evidence of an effect (subject to priors and costs).",
    ]
    axes[1].text(0, 1, "\n".join(lines), va="top", ha="left", fontsize=10, family="monospace")
    fig.suptitle("Synthetic A/B summary", y=1.02)
    fig.tight_layout()
    out = OUT_DIR / "ab_summary.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
