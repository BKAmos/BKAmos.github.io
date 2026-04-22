"""Synthetic viability vs concentration (Hill equation + noise)."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RNG = np.random.default_rng(42)

# Ground-truth Hill: E = E0 + (Emax-E0) * c^h / (EC50^h + c^h)
E0, EMAX, EC50_TRUE, HILL = 0.08, 0.92, 1.4, 1.35


def hill(c: np.ndarray, e0: float, emax: float, ec50: float, h: float) -> np.ndarray:
    c = np.maximum(c, 1e-6)
    return e0 + (emax - e0) * (c**h) / (ec50**h + c**h)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conc = np.logspace(-1.2, 1.1, 14)
    reps = 4
    rows = []
    for c in conc:
        mean_v = hill(np.array([c]), E0, EMAX, EC50_TRUE, HILL)[0]
        for _ in range(reps):
            v = np.clip(mean_v + RNG.normal(0, 0.04), 0, 1)
            rows.append({"concentration_um": float(c), "viability": float(v)})
    pd.DataFrame(rows).to_csv(DATA_DIR / "dose_response.csv", index=False)
    print(f"Wrote {DATA_DIR / 'dose_response.csv'}")


if __name__ == "__main__":
    main()
