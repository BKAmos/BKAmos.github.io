"""Price/cost scenarios with constant elasticity; plot margin."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"


def margin(price: float, cost: float, volume: float) -> float:
    return (price - cost) * volume


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = pd.read_csv(DATA_DIR / "baseline.csv")
    b = dict(zip(base["metric"], base["value"]))
    p0, c0, q0 = float(b["price"]), float(b["unit_cost"]), float(b["base_volume"])

    # Scenarios: (label, price_pct_change, cost_pct_change, elasticity)
    scenarios = [
        ("Base", 0.0, 0.0, -1.2),
        ("Price +5%", 0.05, 0.0, -1.2),
        ("Price −5%", -0.05, 0.0, -1.2),
        ("Cost +8%", 0.0, 0.08, -1.2),
        ("Price +3%, cost +3%", 0.03, 0.03, -1.2),
        ("Price +5%, elast −0.8", 0.05, 0.0, -0.8),
        ("Price +5%, elast −1.8", 0.05, 0.0, -1.8),
    ]
    rows = []
    m0 = margin(p0, c0, q0)
    for label, dp, dc, eps in scenarios:
        p = p0 * (1 + dp)
        c = c0 * (1 + dc)
        q = q0 * (p / p0) ** eps
        m = margin(p, c, q)
        rows.append(
            {
                "scenario": label,
                "price": round(p, 2),
                "unit_cost": round(c, 2),
                "volume": round(q, 0),
                "margin": round(m, 0),
                "margin_vs_base_pct": round(100 * (m - m0) / m0, 1),
            }
        )
    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUT_DIR / "margin_scenarios.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(rows))
    ax.bar(x, out_df["margin"], color="#157878")
    ax.set_xticks(x, out_df["scenario"], rotation=25, ha="right")
    ax.set_ylabel("Gross margin ($)")
    ax.set_title("Margin under illustrative price/cost/elasticity scenarios (synthetic baseline)")
    fig.tight_layout()
    out_png = OUT_DIR / "margin_scenarios.png"
    fig.savefig(out_png, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_png} and {OUT_DIR / 'margin_scenarios.csv'}")


if __name__ == "__main__":
    main()
