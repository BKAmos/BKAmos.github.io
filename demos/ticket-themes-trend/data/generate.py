"""Generate synthetic support tickets with theme and week (CSV)."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RNG = np.random.default_rng(42)

THEMES = ["billing", "bug", "how_to", "performance", "account"]


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    n_weeks = 26
    n_tickets = 1200
    week = RNG.integers(0, n_weeks, size=n_tickets)
    # Drift: later weeks favor "performance" slightly
    base_p = np.array([0.25, 0.2, 0.2, 0.2, 0.15])
    themes = []
    for w in week:
        p = base_p.copy()
        p[3] += 0.003 * w  # performance
        p[0] -= 0.001 * w  # billing down a touch
        p = np.clip(p, 0.05, None)
        p = p / p.sum()
        themes.append(RNG.choice(THEMES, p=p))
    subjects = [f"[{t}] synthetic issue #{i+1}" for i, t in enumerate(themes)]
    df = pd.DataFrame({"week_index": week, "theme": themes, "subject": subjects})
    df.to_csv(DATA_DIR / "tickets.csv", index=False)
    print(f"Wrote {DATA_DIR / 'tickets.csv'}")


if __name__ == "__main__":
    main()
