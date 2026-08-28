"""Static demo positions snapshot, for testing the pairing/plotting pipeline
without a live IBKR connection.
"""

from __future__ import annotations

from pictor.models import OptionLeg
from pictor.pairing import parse_leg

DEMO_POSITIONS = [  # snapshot pulled 2026-08-28 via IBKR get_account_positions
    {"contract_description": "AAOI Sep11'26 100 PUT", "position": 1, "unrealized_pnl": -37.37},
    {"contract_description": "AAOI Sep11'26 120 PUT", "position": -1, "unrealized_pnl": -300.03},
    {"contract_description": "AMAT Sep18'26 450 PUT", "position": 1, "unrealized_pnl": -30.86},
    {"contract_description": "AMAT Sep18'26 470 PUT", "position": -1, "unrealized_pnl": -77.62},
    {"contract_description": "AMD Sep04'26 460 PUT", "position": 1, "unrealized_pnl": -1193.44},
    {"contract_description": "AMD Sep04'26 480 PUT", "position": -1, "unrealized_pnl": 1011.89},
    {"contract_description": "CRWD Sep18'26 190 PUT", "position": 1, "unrealized_pnl": -343.57},
    {"contract_description": "CRWD Sep18'26 210 PUT", "position": -1, "unrealized_pnl": 595.25},
    {"contract_description": "GLD Sep25'26 360 PUT", "position": 1, "unrealized_pnl": -147.09},
    {"contract_description": "GLD Sep25'26 390 PUT", "position": -1, "unrealized_pnl": 615.55},
    {"contract_description": "GLD Sep30'26 385 PUT", "position": 1, "unrealized_pnl": -2.54},
    {"contract_description": "GLD Sep30'26 415 PUT", "position": -1, "unrealized_pnl": -39.82},
    {"contract_description": "META Sep18'26 550 PUT", "position": 2, "unrealized_pnl": -209.69},
    {"contract_description": "META Sep18'26 570 PUT", "position": -2, "unrealized_pnl": -158.04},
    {"contract_description": "NBIS Sep11'26 200 PUT", "position": 1, "unrealized_pnl": -237.79},
    {"contract_description": "NBIS Sep11'26 220 PUT", "position": -1, "unrealized_pnl": 50.49},
    {"contract_description": "NBIS Sep25'26 230 PUT", "position": 1, "unrealized_pnl": 1276.37},
    {"contract_description": "NBIS Sep25'26 250 PUT", "position": -1, "unrealized_pnl": -1927.72},
    {"contract_description": "PANW Sep18'26 300 PUT", "position": 1, "unrealized_pnl": -682.92},
    {"contract_description": "PANW Sep18'26 320 PUT", "position": -1, "unrealized_pnl": 1029.97},
    {"contract_description": "SOXX Sep18'26 465 PUT", "position": 1, "unrealized_pnl": -1192.37},
    {"contract_description": "SOXX Sep18'26 495 PUT", "position": -1, "unrealized_pnl": 1524.22},
    {"contract_description": "SOXX Sep25'26 450 PUT", "position": 1, "unrealized_pnl": -356.78},
    {"contract_description": "SOXX Sep25'26 480 PUT", "position": -1, "unrealized_pnl": 631.38},
    {"contract_description": "SPY Sep18'26 735 PUT", "position": 1, "unrealized_pnl": -297.32},
    {"contract_description": "SPY Sep18'26 755 PUT", "position": -1, "unrealized_pnl": 402.68},
    {"contract_description": "SPY Sep25'26 730 PUT", "position": 1, "unrealized_pnl": -108.64},
    {"contract_description": "SPY Sep25'26 750 PUT", "position": -1, "unrealized_pnl": 200.02},
]


def fetch_positions_demo() -> list[OptionLeg]:
    legs = []
    for row in DEMO_POSITIONS:
        leg = parse_leg(row["contract_description"], row["position"], row["unrealized_pnl"])
        if leg:
            legs.append(leg)
    return legs
