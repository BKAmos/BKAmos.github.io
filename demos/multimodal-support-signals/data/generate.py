"""Generate synthetic multimodal support records (CSV)."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RNG = np.random.default_rng(42)

THEMES = ["billing", "bug", "how_to", "performance", "account"]
PRODUCTS = ["Alpha", "Bravo", "Charlie"]
CHANNELS = ["email", "chat", "phone"]

SNIPPETS = {
    "billing": (
        "Invoice total mismatch",
        "The amount charged does not match our purchase order for last cycle.",
    ),
    "bug": (
        "Export fails intermittently",
        "When exporting CSV over 5k rows the job hangs and eventually times out.",
    ),
    "how_to": (
        "Reset SSO for contractor",
        "We need steps to reset single sign-on for a contractor who lost device access.",
    ),
    "performance": (
        "Dashboard loads slowly",
        "The executive dashboard takes more than twenty seconds to render on Monday mornings.",
    ),
    "account": (
        "Cannot add new seat",
        "The admin panel returns an error when we try to add a seat to our subscription.",
    ),
}


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    n_weeks = 26
    n = 1200
    week = RNG.integers(0, n_weeks, size=n)
    base_p = np.array([0.25, 0.2, 0.2, 0.2, 0.15])
    themes = []
    for w in week:
        p = base_p.copy()
        p[3] += 0.003 * w
        p[0] -= 0.001 * w
        p = np.clip(p, 0.05, None)
        p = p / p.sum()
        themes.append(RNG.choice(THEMES, p=p))

    rows = []
    for i, (w, theme) in enumerate(zip(week, themes)):
        subj, body_base = SNIPPETS[theme]
        subject = f"[{theme}] {subj} #{i+1}"
        body = body_base + " " + RNG.choice(
            [
                "Priority high.",
                "Blocking our release.",
                "Need guidance by Friday.",
                "Occurs on latest build only.",
            ]
        )
        product_line = RNG.choice(PRODUCTS)
        channel = RNG.choice(CHANNELS, p=[0.45, 0.35, 0.2])
        attachment_kb = int(
            RNG.choice([0, 0, 0, 120, 450, 900], p=[0.5, 0.15, 0.1, 0.1, 0.1, 0.05])
        )
        rows.append(
            {
                "week_index": w,
                "theme": theme,
                "subject": subject,
                "body": body,
                "product_line": product_line,
                "channel": channel,
                "attachment_kb": attachment_kb,
            }
        )

    pd.DataFrame(rows).to_csv(DATA_DIR / "support_records.csv", index=False)
    print(f"Wrote {DATA_DIR / 'support_records.csv'}")


if __name__ == "__main__":
    main()
