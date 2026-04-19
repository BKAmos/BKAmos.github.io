"""Generate synthetic customer feature table (CSV)."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RNG = np.random.default_rng(42)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    n = 500
    # Three latent groups
    group = RNG.integers(0, 3, size=n)
    base = np.array([[800, 12, 24], [2200, 28, 8], [1200, 6, 48]])[group]
    noise = RNG.normal(0, [120, 4, 10], size=(n, 3))
    annual_spend = np.clip(base[:, 0] + noise[:, 0], 50, None)
    visits = np.clip(base[:, 1] + noise[:, 1], 1, None)
    tenure_months = np.clip(base[:, 2] + noise[:, 2], 1, None)
    df = pd.DataFrame(
        {
            "customer_id": range(1, n + 1),
            "annual_spend": annual_spend.round(2),
            "visit_count_annual": visits.round(1),
            "tenure_months": tenure_months.round(1),
        }
    )
    df.to_csv(DATA_DIR / "customers.csv", index=False)
    print(f"Wrote {DATA_DIR / 'customers.csv'}")


if __name__ == "__main__":
    main()
