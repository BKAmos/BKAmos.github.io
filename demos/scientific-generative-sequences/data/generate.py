"""Save a synthetic DNA PWM (motif) and background base frequencies."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RNG = np.random.default_rng(42)

BASES = list("ACGT")
L_MOTIF = 12


def softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Logits favor a G-rich core (synthetic binding site)
    logits = np.array(
        [
            [0.2, -0.3, 0.1, 0.4],
            [-0.2, 0.1, 0.5, 0.0],
            [0.0, -0.4, 0.8, -0.2],
            [-0.5, 0.2, 1.0, -0.4],
            [-0.3, -0.2, 1.2, -0.5],
            [-0.4, 0.0, 1.1, -0.3],
            [0.1, -0.3, 0.9, -0.2],
            [0.0, 0.2, 0.6, -0.1],
            [0.3, -0.1, 0.2, 0.1],
            [-0.1, 0.0, 0.5, -0.2],
            [0.2, 0.1, 0.3, -0.1],
            [0.1, -0.2, 0.2, 0.0],
        ]
    )
    logits = logits + RNG.normal(0, 0.08, size=logits.shape)
    pwm = softmax(logits)
    rows = []
    for i in range(L_MOTIF):
        for b, p in zip(BASES, pwm[i]):
            rows.append({"position": i, "base": b, "probability": float(p)})
    pd.DataFrame(rows).to_csv(DATA_DIR / "motif_pwm_long.csv", index=False)

    bg = np.array([0.26, 0.24, 0.25, 0.25]) + RNG.normal(0, 0.01, size=4)
    bg = np.clip(bg, 0.05, None)
    bg = bg / bg.sum()
    pd.DataFrame([dict(zip(BASES, bg))]).to_csv(DATA_DIR / "background_nt.csv", index=False)
    print(f"Wrote PWM and background under {DATA_DIR}")


if __name__ == "__main__":
    main()
