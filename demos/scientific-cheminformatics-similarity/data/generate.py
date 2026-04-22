"""Synthetic compounds: 64-bit fingerprints and physicochemical descriptors (no RDKit)."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RNG = np.random.default_rng(42)

N = 120
FP_BITS = 64


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Three scaffold families: similar intra-group fingerprints
    centers = RNG.integers(0, 2, size=(3, FP_BITS), dtype=np.uint8)
    cluster = RNG.integers(0, 3, size=N)
    fps = []
    for i in range(N):
        c = cluster[i]
        flip = RNG.random(FP_BITS) < 0.12
        bits = np.where(flip, 1 - centers[c], centers[c])
        fps.append(bits.astype(np.uint8))

    # Physicochemical-style descriptors (synthetic but correlated with cluster)
    rows = []
    for i in range(N):
        k = cluster[i]
        fp = fps[i]
        on = int(fp.sum())
        mw = 220 + 85 * k + 1.1 * on + RNG.normal(0, 18)
        logp = -0.4 + 0.9 * k + 0.04 * on + RNG.normal(0, 0.35)
        tpsa = 40 + 22 * (2 - k) + 0.35 * on + RNG.normal(0, 12)
        rows.append(
            {
                "compound_id": f"CMP-{i:03d}",
                "cluster": int(k),
                "mw": round(float(mw), 2),
                "logp": round(float(logp), 3),
                "tpsa": round(float(tpsa), 2),
                "fingerprint": "".join(str(int(b)) for b in fp),
            }
        )

    pd.DataFrame(rows).to_csv(DATA_DIR / "compounds.csv", index=False)
    print(f"Wrote {DATA_DIR / 'compounds.csv'}")


if __name__ == "__main__":
    main()
