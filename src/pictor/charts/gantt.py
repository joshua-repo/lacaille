"""Interactive expiry Gantt chart for vertical spreads, with configurable
per-ticker decision zones and earnings / recent-news flags.
"""

from __future__ import annotations

import datetime as dt

import plotly.graph_objects as go

from pictor.enrichment import NEWS_LOOKBACK_DAYS, enrich_tickers
from pictor.models import Spread

# Per-ticker decision zone thresholds, in days-to-expiry. Anything without an
# explicit entry falls back to DEFAULT -- edit this dict, or pass your own
# via build_chart(..., decision_zone_days=...).
DECISION_ZONE_DAYS: dict[str, int] = {
    "DEFAULT": 10,
    "PANW": 14,   # example: want more runway around earnings-heavy names
    "NBIS": 5,    # example: comfortable holding high-IV names closer to expiry
}

GAIN_COLOR = "#0ca30c"
LOSS_COLOR = "#d03b3b"
ZONE_COLOR = "rgba(250, 178, 25, 0.25)"
NEWS_COLOR = "#eda100"


def build_chart(
    spreads: list[Spread],
    today: dt.date | None = None,
    decision_zone_days: dict[str, int] | None = None,
) -> go.Figure:
    today = today or dt.date.today()
    decision_zone_days = decision_zone_days or DECISION_ZONE_DAYS
    spreads = sorted(spreads, key=lambda s: (s.expiry - today).days)
    labels = [s.label for s in spreads]
    enrichment = enrich_tickers([s.underlying for s in spreads])

    fig = go.Figure()

    for i, s in enumerate(spreads):
        dte = (s.expiry - today).days
        color = GAIN_COLOR if s.unrealized_pnl >= 0 else LOSS_COLOR

        earnings = enrichment[s.underlying].earnings_date
        flagged = earnings is not None and today <= earnings <= s.expiry
        news = enrichment[s.underlying].news

        hover = (
            f"<b>{s.label}</b><br>"
            f"Expiry: {s.expiry:%Y-%m-%d} ({dte}d)<br>"
            f"Unrealized P&L: ${s.unrealized_pnl:,.0f}"
        )
        if flagged:
            hover += f"<br><b>Earnings {earnings:%b %d}</b> falls before expiry"
        if news:
            hover += f"<br><b>Recent headline</b> in the last {NEWS_LOOKBACK_DAYS}d"

        fig.add_trace(
            go.Bar(
                x=[dte],
                y=[s.label],
                base=0,
                orientation="h",
                marker=dict(color=color, line=dict(color=LOSS_COLOR if flagged else color, width=2 if flagged else 0)),
                hovertemplate=hover + "<extra></extra>",
                showlegend=False,
            )
        )

        zone_days = decision_zone_days.get(s.underlying, decision_zone_days["DEFAULT"])
        fig.add_shape(
            type="rect",
            xref="x",
            yref="y",
            x0=0,
            x1=zone_days,
            y0=i - 0.4,
            y1=i + 0.4,
            fillcolor=ZONE_COLOR,
            line=dict(width=0),
            layer="below",
        )

        if flagged:
            fig.add_trace(
                go.Scatter(
                    x=[(earnings - today).days],
                    y=[s.label],
                    mode="markers",
                    marker=dict(symbol="diamond", size=10, color=LOSS_COLOR),
                    hovertemplate=f"Earnings {earnings:%b %d}<extra></extra>",
                    showlegend=False,
                )
            )
        if news:
            fig.add_trace(
                go.Scatter(
                    x=[dte + 0.6],
                    y=[s.label],
                    mode="markers",
                    marker=dict(symbol="star", size=11, color=NEWS_COLOR),
                    hovertemplate=f"Recent headline in the last {NEWS_LOOKBACK_DAYS}d<extra></extra>",
                    showlegend=False,
                )
            )

    # legend (dummy traces so real bars/markers stay showlegend=False and clean)
    fig.add_trace(go.Bar(x=[None], y=[None], marker_color=GAIN_COLOR, name="Net gain"))
    fig.add_trace(go.Bar(x=[None], y=[None], marker_color=LOSS_COLOR, name="Net loss"))
    fig.add_trace(
        go.Scatter(
            x=[None], y=[None], mode="markers",
            marker=dict(symbol="diamond", size=10, color=LOSS_COLOR),
            name="Earnings before expiry",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[None], y=[None], mode="markers",
            marker=dict(symbol="star", size=11, color=NEWS_COLOR),
            name="Recent headline",
        )
    )

    fig.update_yaxes(categoryorder="array", categoryarray=labels, autorange="reversed")
    fig.update_layout(
        template="plotly_white",
        height=max(360, 40 * len(spreads) + 140),
        margin=dict(l=140, r=40, t=60, b=40),
        xaxis_title="Days to expiry",
        bargap=0.35,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig
