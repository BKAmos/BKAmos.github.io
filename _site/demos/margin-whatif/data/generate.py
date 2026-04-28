"""Write baseline price, cost, and volume for scenario math (CSV)."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        {
            "metric": ["price", "unit_cost", "base_volume"],
            "value": [49.99, 22.50, 10_000],
        }
    )
    df.to_csv(DATA_DIR / "baseline.csv", index=False)
    print(f"Wrote {DATA_DIR / 'baseline.csv'}")


if __name__ == "__main__":
    main()
