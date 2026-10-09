"""Charts, drawn by matplotlib to SVG with the text left as text.

matplotlib does the geometry; the browser sets the type in the brand's fonts,
which matplotlib alone cannot reliably do with variable fonts. Fonts are still
registered here so that matplotlib *measures* text with the right metrics and
lays the axes out for the glyphs that will actually be drawn.

Every chart labels its axes and units itself, from the chart kind -- a caller
cannot forget them.
"""

from __future__ import annotations

import datetime as dt
import io

from pictor.publish.brand import Brand

Series = list[tuple[dt.date, float]]


def _setup(brand: Brand):
    import logging

    import matplotlib

    # A variable font has one face to matplotlib, so it reports every bold
    # label as "falling back to 400". Only the metrics come from matplotlib;
    # the browser draws the real bold. The warning is noise here.
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

    matplotlib.use("Agg")
    from matplotlib import font_manager

    for f in brand.fonts:
        font_manager.fontManager.addfont(str(f.path))
    import matplotlib.pyplot as plt

    c = brand.color
    plt.rcParams.update({
        "svg.fonttype": "none",
        "font.family": brand.body,
        "font.size": 10,
        "axes.edgecolor": c["rule"],
        "axes.labelcolor": c["sub"],
        "xtick.color": c["muted"],
        "ytick.color": c["muted"],
    })
    return plt


def equity_vs_baseline(
    brand: Brand,
    treatment: Series,
    baseline: Series,
    labels: tuple[str, str],
    initial: float,
    size: tuple[float, float],
) -> str:
    """Trading P&L of both arms over the window, as a percentage of the
    starting account, cash interest excluded -- the carry is the same for both
    arms and would otherwise dominate the line (see `runs.trading_pnl`).

    The treatment line ends in the accent dot, as the brand's mark does; both
    lines are labelled at their ends instead of through a legend box.
    """
    plt = _setup(brand)
    import matplotlib.dates as mdates
    import matplotlib.ticker as mticker

    c = brand.color
    fig, ax = plt.subplots(figsize=size)
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")

    def rebased(series: Series):
        return [d for d, _ in series], [v / initial * 100 for _, v in series]

    tx, ty = rebased(treatment)
    bx, by = rebased(baseline)
    ax.axhline(0, color=c["rule"], lw=1, zorder=1)
    ax.plot(bx, by, color=c["base"], lw=1.6, zorder=2)
    ax.plot(tx, ty, color=c["treat"], lw=2.2, zorder=3)
    ax.plot([tx[-1]], [ty[-1]], "o", ms=7, color=c["accent"], zorder=4)
    ax.annotate(labels[0], (tx[-1], ty[-1]), xytext=(8, 0), textcoords="offset points",
                va="center", color=c["treat"], fontsize=10, fontweight="bold")
    ax.annotate(labels[1], (bx[-1], by[-1]), xytext=(8, 0), textcoords="offset points",
                va="center", color=c["base"], fontsize=10)

    ax.set_ylabel(f"Trading P&L, % of ${initial:,.0f}, excl. cash interest", fontsize=9)
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: "0%" if abs(v) < 1e-9 else f"{v:+.1f}%")
    )
    locator = mdates.AutoDateLocator(minticks=3, maxticks=6)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.grid(axis="y", color=c["grid"], lw=0.8)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0, pad=6)

    # Room on the right for the end labels -- room, not time, so no tick in it.
    span = tx[-1] - tx[0]
    ax.set_xlim(tx[0], tx[-1] + span * 0.34)
    last = mdates.date2num(tx[-1])
    ax.set_xticks([t for t in ax.get_xticks() if t <= last])

    fig.tight_layout(pad=0.2)
    buf = io.StringIO()
    fig.savefig(buf, format="svg", transparent=True)
    plt.close(fig)
    return buf.getvalue().split("?>", 1)[-1].strip()
