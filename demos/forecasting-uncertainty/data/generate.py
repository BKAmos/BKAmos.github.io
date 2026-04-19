"""Generate synthetic monthly demand (CSV)."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RNG = np.random.default_rng(42)

def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    n = 60
    t = np.arange(n)
    level = 100 + 0.4 * t
    seasonal = 12 * np.sin(2 * np.pi * (t % 12) / 12)
    noise = RNG.normal(0, 8, size=n)
    demand = np.clip(level + seasonal + noise, 20, None)
    months = pd.date_range("2019-01-01", periods=n, freq="MS")
    df = pd.DataFrame({"month": months.strftime("%Y-%m-%d"), "demand": demand.round(2)})
    df.to_csv(DATA_DIR / "monthly_demand.csv", index=False)
    print(f"Wrote {DATA_DIR / 'monthly_demand.csv'}")


if __name__ == "__main__":
    main()
