"""Synthetic samples: expression panel, imaging-style features, clinical covariates."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RNG = np.random.default_rng(42)

N = 80
N_GENES = 10


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    age = RNG.normal(58, 12, size=N)
    sex = RNG.integers(0, 2, size=N)
    # Latent disease axis drives expression and imaging
    axis = RNG.normal(0, 1, size=N)
    group = (axis > 0.15).astype(int)

    # Expression (log-scale toy)
    W = RNG.normal(0, 0.45, size=(N_GENES, 2))
    z = np.column_stack([axis, age / 40.0, sex])
    base = z @ RNG.normal(0, 0.5, size=(3, N_GENES))
    signal = (axis[:, None] * W[None, :, 0]) + (group[:, None] * 0.35 * W[None, :, 1])
    expr = 6.0 + base + signal + RNG.normal(0, 0.25, size=(N, N_GENES))

    # Imaging-style features (texture, size, intensity)
    img1 = 0.55 * axis + 0.02 * age + RNG.normal(0, 0.2, size=N)
    img2 = -0.35 * axis + 0.15 * sex + RNG.normal(0, 0.25, size=N)
    img3 = 0.2 * axis**2 + RNG.normal(0, 0.18, size=N)

    rows = []
    for i in range(N):
        row = {
            "sample_id": f"S{i:03d}",
            "group": int(group[i]),
            "age": round(float(age[i]), 1),
            "sex_male": int(sex[i]),
            "img_texture": round(float(img1[i]), 4),
            "img_size_mm": round(float(img2[i]), 4),
            "img_intensity": round(float(img3[i]), 4),
        }
        for g in range(N_GENES):
            row[f"expr_g{g:02d}"] = round(float(expr[i, g]), 4)
        rows.append(row)

    pd.DataFrame(rows).to_csv(DATA_DIR / "samples.csv", index=False)
    print(f"Wrote {DATA_DIR / 'samples.csv'}")


if __name__ == "__main__":
    main()
