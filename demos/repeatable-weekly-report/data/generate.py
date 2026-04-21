"""Generate synthetic weekly KPIs and incidents (CSVs)."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RNG = np.random.default_rng(42)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    weeks = pd.period_range("2025-01-06", periods=8, freq="W-MON")
    base_rev = 120_000
    rev = base_rev + np.cumsum(RNG.normal(0, 4000, size=len(weeks)))
    orders = (rev / 85 + RNG.normal(0, 120, size=len(weeks))).astype(int)
    returns = (RNG.poisson(18, size=len(weeks)))
    kpi = pd.DataFrame(
        {
            "week_start": weeks.astype(str),
            "revenue": rev.round(0),
            "orders": orders,
            "returns": returns,
        }
    )
    kpi.to_csv(DATA_DIR / "weekly_kpis.csv", index=False)

    incidents = pd.DataFrame(
        {
            "week_start": ["2025-02-03", "2025-02-17"],
            "severity": ["SEV2", "SEV3"],
            "summary": [
                "Synthetic latency spike on checkout API",
                "Synthetic email delay for password resets",
            ],
        }
    )
    incidents.to_csv(DATA_DIR / "incidents.csv", index=False)
    print(f"Wrote {DATA_DIR / 'weekly_kpis.csv'} and {DATA_DIR / 'incidents.csv'}")


if __name__ == "__main__":
    main()
