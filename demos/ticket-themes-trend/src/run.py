"""Aggregate tickets by week/theme and plot stacked area."""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATA_DIR / "tickets.csv")
    counts = (
        df.groupby(["week_index", "theme"])
        .size()
        .unstack(fill_value=0)
        .sort_index()
    )
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.stackplot(
        counts.index,
        *[counts[c] for c in counts.columns],
        labels=counts.columns,
        alpha=0.85,
    )
    ax.set_title("Synthetic support tickets by theme (weekly)")
    ax.set_xlabel("Week index")
    ax.set_ylabel("Ticket count")
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1))
    fig.tight_layout()
    out = OUT_DIR / "ticket_themes.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
