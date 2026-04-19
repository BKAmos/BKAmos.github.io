"""Fit additive ETS and plot forecast with 80% prediction interval."""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from statsmodels.tsa.exponential_smoothing.ets import ETSModel

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATA_DIR / "monthly_demand.csv", parse_dates=["month"])
    y = df.set_index("month")["demand"].asfreq("MS")
    model = ETSModel(
        y,
        error="add",
        trend="add",
        seasonal="add",
        seasonal_periods=12,
    )
    fit = model.fit(disp=False)
    horizon = 12
    pred = fit.get_prediction(start=len(y), end=len(y) + horizon - 1)
    frame = pred.summary_frame(alpha=0.2)
    mean_fc = frame["mean"]
    low = frame["pi_lower"]
    high = frame["pi_upper"]

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(y.index, y.values, label="History", color="#157878")
    ax.plot(mean_fc.index, mean_fc.values, label="Forecast", color="#c44e52")
    ax.fill_between(
        mean_fc.index,
        low,
        high,
        color="#c44e52",
        alpha=0.2,
        label="80% interval",
    )
    ax.set_title("Monthly demand — forecast with 80% prediction interval")
    ax.set_xlabel("Month")
    ax.set_ylabel("Units")
    ax.legend(loc="upper left")
    fig.tight_layout()
    out = OUT_DIR / "forecast.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
