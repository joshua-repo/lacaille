"""IbkrBroker against a fake `ib`: the socket it opens, the guard, the conversions."""

from __future__ import annotations

import datetime as dt
import subprocess
import sys

import pytest

from antlia import auth
from puppis.guard import NotPaper
from puppis.ibkr import CLIENT_ID, IbkrBroker
from tests.puppis.fakes import STARTUP_NONE, FakeIB, fake_sdk


@pytest.fixture
def paper_port(monkeypatch):
    monkeypatch.setenv("ANTLIA_IBKR_PAPER_PORT", "4002")


def connected(ib: FakeIB) -> IbkrBroker:
    broker = IbkrBroker(sdk=fake_sdk(ib))  # type: ignore[arg-type]
    broker.connect()
    return broker


def test_it_opens_its_own_writable_socket_and_syncs_nothing(paper_port):
    ib = FakeIB()
    connected(ib)
    assert ib.connected_with == {
        "host": "127.0.0.1",
        "port": 4002,
        "clientId": CLIENT_ID,
        "readonly": False,
        "timeout": 10.0,
        "fetchFields": STARTUP_NONE,
    }
    assert CLIENT_ID < 900  # below antlia's auto-allocated range


def test_a_live_account_disconnects_before_anything_is_asked(paper_port):
    ib = FakeIB(accounts=["U16200976"])
    with pytest.raises(NotPaper):
        connected(ib)
    assert ib.calls == ["connect", "managedAccounts", "disconnect"]


def test_no_port_is_a_clear_error_not_a_default(monkeypatch):
    monkeypatch.setattr(auth, "credential", lambda *a, **k: {"host": "127.0.0.1"})
    with pytest.raises(RuntimeError, match="4002"):
        IbkrBroker(sdk=fake_sdk(FakeIB())).connect()  # type: ignore[arg-type]


def test_positions_are_puppis_types(paper_port):
    short_put, shares = connected(FakeIB()).positions()
    assert short_put.instrument.expiration == dt.date(2026, 11, 20)
    assert (short_put.instrument.strike, short_put.instrument.right) == (550.0, "P")
    assert short_put.instrument.multiplier == 100.0
    assert short_put.quantity == -2.0
    # A stock's empty option fields are None, not "", 0.0 or a bad date.
    assert (shares.instrument.expiration, shares.instrument.strike, shares.instrument.right) == (
        None,
        None,
        None,
    )
    assert shares.instrument.multiplier == 1.0


def test_a_commission_is_known_only_once_its_report_arrived(paper_port):
    reported, pending = connected(FakeIB()).executions()
    assert (reported.commission, pending.commission) == (1.3, None)
    assert reported.order_ref == "p-1" and reported.side == "SLD"
    assert reported.time.tzinfo is dt.UTC


def test_nothing_is_asked_before_connect():
    with pytest.raises(RuntimeError, match="not connected"):
        IbkrBroker().positions()


def test_importing_puppis_loads_no_sdk():
    out = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, puppis, puppis.cli;"
            "print(sorted({'ib_async', 'ib_insync', 'ibapi'} & set(sys.modules)))",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert out.strip() == "[]"
