"""Generate synthetic A/B samples (CSV)."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RNG = np.random.default_rng(42)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    n_control = 400
    n_treatment = 380
    control = RNG.normal(loc=42.0, scale=8.0, size=n_control)
    treatment = RNG.normal(loc=44.5, scale=8.5, size=n_treatment)
    df = pd.concat(
        [
            pd.DataFrame({"arm": "control", "metric": control}),
            pd.DataFrame({"arm": "treatment", "metric": treatment}),
        ],
        ignore_index=True,
    )
    df.to_csv(DATA_DIR / "experiment.csv", index=False)
    print(f"Wrote {DATA_DIR / 'experiment.csv'}")


if __name__ == "__main__":
    main()
