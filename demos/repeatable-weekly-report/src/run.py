"""Render weekly report HTML from CSVs using Jinja2."""
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"
TEMPLATE_DIR = Path(__file__).resolve().parent


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    kpi = pd.read_csv(DATA_DIR / "weekly_kpis.csv")
    incidents = pd.read_csv(DATA_DIR / "incidents.csv")
    report_week = str(kpi["week_start"].iloc[-1])

    last = kpi.iloc[-1]
    prev = kpi.iloc[-2] if len(kpi) > 1 else last
    rev_delta = 100 * (last["revenue"] - prev["revenue"]) / prev["revenue"]
    ord_delta = 100 * (last["orders"] - prev["orders"]) / prev["orders"]
    highlights = [
        f"Revenue for latest week: ${last['revenue']:,.0f} ({rev_delta:+.1f}% vs prior week).",
        f"Orders: {int(last['orders'])} ({ord_delta:+.1f}% vs prior week).",
        f"Returns (count): {int(last['returns'])}.",
    ]

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("report.html.j2")
    html = template.render(
        report_week=report_week,
        highlights=highlights,
        kpi_table=kpi.to_html(index=False, classes=None),
        incidents=incidents,
        incidents_table=incidents.to_html(index=False),
    )
    out = OUT_DIR / "report.html"
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
