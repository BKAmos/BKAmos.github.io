"""Render weekly report HTML from CSVs using Jinja2 (English and Spanish)."""
import json
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"
TEMPLATE_DIR = Path(__file__).resolve().parent


def load_strings(locale: str) -> dict:
    path = TEMPLATE_DIR / f"strings_{locale}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def build_highlights(locale: str, last, rev_delta: float, ord_delta: float) -> list[str]:
    rev = float(last["revenue"])
    orders = int(last["orders"])
    returns = int(last["returns"])
    if locale == "en":
        return [
            f"Revenue for latest week: ${rev:,.0f} ({rev_delta:+.1f}% vs prior week).",
            f"Orders: {orders} ({ord_delta:+.1f}% vs prior week).",
            f"Returns (count): {returns}.",
        ]
    return [
        f"Ingresos de la última semana: {rev:,.0f} USD ({rev_delta:+.1f}% respecto a la semana anterior).",
        f"Pedidos: {orders} ({ord_delta:+.1f}% respecto a la semana anterior).",
        f"Devoluciones (recuento): {returns}.",
    ]


def render_locale(locale: str, kpi: pd.DataFrame, incidents: pd.DataFrame) -> None:
    t = load_strings(locale)
    report_week = str(kpi["week_start"].iloc[-1])
    last = kpi.iloc[-1]
    prev = kpi.iloc[-2] if len(kpi) > 1 else last
    rev_delta = 100 * (last["revenue"] - prev["revenue"]) / prev["revenue"]
    ord_delta = 100 * (last["orders"] - prev["orders"]) / prev["orders"]
    highlights = build_highlights(locale, last, rev_delta, ord_delta)

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("report.html.j2")
    html = template.render(
        t=t,
        report_week=report_week,
        highlights=highlights,
        kpi_table=kpi.to_html(index=False, classes=None),
        incidents=incidents,
        incidents_table=incidents.to_html(index=False),
    )
    out = OUT_DIR / f"report_{locale}.html"
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    kpi = pd.read_csv(DATA_DIR / "weekly_kpis.csv")
    incidents = pd.read_csv(DATA_DIR / "incidents.csv")
    for locale in ("en", "es"):
        render_locale(locale, kpi, incidents)
    # Backward-compatible default (English)
    (OUT_DIR / "report.html").write_text(
        (OUT_DIR / "report_en.html").read_text(encoding="utf-8"), encoding="utf-8"
    )
    print(f"Wrote {OUT_DIR / 'report.html'} (copy of English)")


if __name__ == "__main__":
    main()
