"""Parsing IBKR contract descriptions into legs, and pairing legs into
vertical spreads. Decoupled from any particular data source -- feed it
OptionLeg objects from antlia, IBKR MCP, a local JSON dump, whatever.
"""

from __future__ import annotations

import datetime as dt
import re
from collections import defaultdict

from pictor.models import OptionLeg, Spread

DESC_RE = re.compile(
    r"^(?P<sym>[A-Z]+)\s+(?P<mon>[A-Za-z]{3})(?P<day>\d{2})'(?P<yr>\d{2})\s+"
    r"(?P<strike>[\d.]+)\s+(?P<right>PUT|CALL)"
)


def parse_leg(desc: str, position: float, pnl: float) -> OptionLeg | None:
    m = DESC_RE.match(desc)
    if not m:
        return None
    month = dt.datetime.strptime(m["mon"], "%b").month
    year = 2000 + int(m["yr"])
    expiry = dt.date(year, month, int(m["day"]))
    right = "C" if m["right"] == "CALL" else "P"
    return OptionLeg(m["sym"], float(m["strike"]), right, expiry, position, pnl)


def pair_spreads(legs: list[OptionLeg]) -> list[Spread]:
    """Group legs by (source, underlying, right, expiry) and pair each long leg
    with a short leg into a vertical spread. Unmatched legs (no opposite-side
    counterpart -- e.g. a standalone long call) are silently dropped; surface
    them separately if you want naked positions tracked too.

    **`source` is part of the key**: a long leg in one broker and a short leg in
    another are not a spread. They carry no common margin, they cannot be closed
    together, and pairing them would invent a position that exists in neither
    account. Legs with no source (a caller feeding its own `OptionLeg`s) all
    share the empty string and pair as before.
    """
    groups: dict[tuple, list[OptionLeg]] = defaultdict(list)
    for leg in legs:
        groups[(leg.source, leg.underlying, leg.right, leg.expiry)].append(leg)

    spreads = []
    for (source, underlying, right, expiry), group in groups.items():
        longs = sorted((g for g in group if g.position > 0), key=lambda g: g.strike)
        shorts = sorted((g for g in group if g.position < 0), key=lambda g: g.strike)
        for lo, sh in zip(longs, shorts):
            spreads.append(
                Spread(
                    underlying=underlying,
                    right=right,
                    expiry=expiry,
                    long_strike=lo.strike,
                    short_strike=sh.strike,
                    unrealized_pnl=lo.unrealized_pnl + sh.unrealized_pnl,
                    source=source,
                )
            )
    return spreads
