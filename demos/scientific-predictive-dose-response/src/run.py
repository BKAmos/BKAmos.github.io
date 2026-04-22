"""Fit Hill curve to viability; plot with bootstrap CI on EC50."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"


def hill(c: np.ndarray, e0: float, emax: float, ec50: float, h: float) -> np.ndarray:
    c = np.maximum(c, 1e-9)
    return e0 + (emax - e0) * (c**h) / (ec50**h + c**h)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATA_DIR / "dose_response.csv")
    x = df["concentration_um"].values
    y = df["viability"].values

    p0 = (0.05, 0.9, 1.0, 1.0)
    bounds = ([0, 0, 0.05, 0.3], [0.5, 1.0, 50.0, 5.0])
    popt, pcov = curve_fit(hill, x, y, p0=p0, bounds=bounds, maxfev=20000)
    e0, emax, ec50, h = popt
    perr = np.sqrt(np.diag(pcov))

    grid = np.logspace(np.log10(x.min() * 0.8), np.log10(x.max() * 1.1), 200)
    yhat = hill(grid, *popt)

    # Residual bootstrap on the fitted curve (toy uncertainty)
    rng = np.random.default_rng(7)
    yfit = hill(x, *popt)
    resid = y - yfit
    pred_samples = []
    for _ in range(500):
        yb = yfit + rng.choice(resid, size=len(y), replace=True)
        try:
            pb, _ = curve_fit(hill, x, yb, p0=popt, bounds=bounds, maxfev=20000)
            pred_samples.append(hill(grid, *pb))
        except RuntimeError:
            pred_samples.append(yhat)
    pred_samples = np.array(pred_samples)
    low = np.percentile(pred_samples, 5, axis=0)
    high = np.percentile(pred_samples, 95, axis=0)

    summary = pd.DataFrame(
        [
            {"parameter": "E0", "estimate": e0, "se_approx": perr[0]},
            {"parameter": "Emax", "estimate": emax, "se_approx": perr[1]},
            {"parameter": "EC50_um", "estimate": ec50, "se_approx": perr[2]},
            {"parameter": "Hill_n", "estimate": h, "se_approx": perr[3]},
        ]
    )
    summary.to_csv(OUT_DIR / "fit_summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.scatter(x, y, s=36, alpha=0.75, color="#157878", label="Observed (synthetic)", zorder=3)
    ax.plot(grid, yhat, color="#c44e52", lw=2, label="Fitted Hill")
    ax.fill_between(grid, low, high, color="#c44e52", alpha=0.2, label="90% bootstrap band (fit)")
    ax.set_xscale("log")
    ax.set_xlabel("Concentration (µM)")
    ax.set_ylabel("Viability")
    ax.set_title("Dose–response fit — Hill equation (synthetic assay noise)")
    ax.legend(loc="lower right")
    ax.set_ylim(-0.02, 1.05)
    fig.tight_layout()
    out = OUT_DIR / "dose_response_fit.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"Wrote {out} and {OUT_DIR / 'fit_summary.csv'}")


if __name__ == "__main__":
    main()
