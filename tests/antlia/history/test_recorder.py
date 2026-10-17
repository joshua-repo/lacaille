"""The recorder: its grid, its refusal to queue, and the log of every attempt."""

from __future__ import annotations

import contextlib
import datetime as dt
from types import SimpleNamespace

import pytest

from antlia import auth, history, live
from antlia.history import attempts, recorder
from antlia.history.cli import main
from antlia.live.sources.ibkr import IBKRLive
from tests.antlia.live.test_option_chain import FakeIB, Option, Stock

UTC = dt.UTC
MONDAY = dt.date(2026, 10, 19)  # New York is UTC-4 in October


def at(hour: int, minute: int = 0, day: dt.date = MONDAY) -> dt.datetime:
    return dt.datetime.combine(day, dt.time(hour, minute), tzinfo=UTC)


@pytest.fixture
def gateway(monkeypatch):
    ib = FakeIB()
    seen: list[dict[str, object]] = []

    @contextlib.contextmanager
    def session(*args, **kwargs):
        seen.append(kwargs)
        yield ib

    monkeypatch.setattr(auth, "session", session)
    monkeypatch.setattr(
        IBKRLive, "require", lambda self, m: SimpleNamespace(Stock=Stock, Option=Option)
    )
    return seen


class TestGrid:
    def test_every_is_read_in_seconds_minutes_or_hours(self):
        assert recorder.parse_every("15m") == dt.timedelta(minutes=15)
        assert recorder.parse_every("30s") == dt.timedelta(seconds=30)
        assert recorder.parse_every("1h") == dt.timedelta(hours=1)
        for bad in ("15", "5s", "fortnightly"):
            with pytest.raises(ValueError):
                recorder.parse_every(bad)

    def test_a_day_runs_from_the_open_to_the_close_inclusive(self):
        ticks = recorder.grid(MONDAY, dt.timedelta(minutes=15))
        assert ticks[0] == at(13, 30) and ticks[-1] == at(20, 0)
        assert len(ticks) == 27

    def test_the_close_is_recorded_even_off_the_step(self):
        ticks = recorder.grid(MONDAY, dt.timedelta(minutes=7))
        assert ticks[-1] == at(20, 0)
        assert ticks[-2] < ticks[-1]

    def test_weekends_have_no_grid(self):
        assert recorder.grid(dt.date(2026, 10, 17), dt.timedelta(minutes=15)) == []

    def test_the_next_tick_skips_the_night_and_the_weekend(self):
        every = dt.timedelta(minutes=15)
        saturday = at(12, 0, dt.date(2026, 10, 17))
        assert recorder.next_tick(saturday, every) == at(13, 30)
        assert recorder.next_tick(at(14, 1), every) == at(14, 15)
        assert recorder.next_tick(at(20, 1), every) == at(13, 30, dt.date(2026, 10, 20))

    def test_ticks_passed_while_busy_are_named_not_queued(self):
        every = dt.timedelta(minutes=15)
        assert recorder.missed(at(13, 30), at(14, 2), every) == [at(13, 45), at(14, 0)]
        assert recorder.missed(at(13, 30), at(13, 40), every) == []


class TestRecordOnce:
    def test_a_snapshot_is_kept_and_logged_ok(self, gateway, tmp_path):
        attempt = recorder.record_once("AAPL", {"strikes": (140, 220)}, at(14), tmp_path)
        assert attempt.status == attempts.OK and attempt.rows > 0
        assert history.option_quotes("AAPL", "2000-01-01", "2100-01-01", store=tmp_path).num_rows
        # Its own client id, so it cannot collide with a hand-run script.
        assert gateway[-1] == {"client_id": recorder.CLIENT_ID}

    def test_an_error_is_a_failed_attempt_not_a_crash(self, monkeypatch, tmp_path):
        def broken(*a, **k):
            raise ConnectionError("gateway restarting")

        monkeypatch.setattr(live, "option_chain", broken)
        attempt = recorder.record_once("AAPL", {}, at(14), tmp_path)
        assert attempt.status == attempts.FAILED
        assert "gateway restarting" in attempt.detail

    def test_nothing_back_is_empty_not_ok(self, gateway, tmp_path):
        attempt = recorder.record_once("AAPL", {"strikes": (1, 2)}, at(14), tmp_path)
        assert (attempt.status, attempt.rows) == (attempts.EMPTY, 0)


def test_an_overrun_skips_what_it_ran_through(monkeypatch, tmp_path):
    clock = {"now": at(13, 29)}

    def slow_chain(symbol, **options):
        clock["now"] += dt.timedelta(minutes=20 if clock["now"] < at(13, 45) else 1)
        return live.Snapshot(
            "option_quote", "ibkr", clock["now"], attempts.SCHEMA.empty_table(), None
        )

    monkeypatch.setattr(live, "option_chain", slow_chain)

    def sleep(seconds: float) -> None:
        clock["now"] += dt.timedelta(seconds=seconds)

    recorder.run(
        "SPY",
        {},
        dt.timedelta(minutes=15),
        tmp_path,
        clock=lambda: clock["now"],
        sleep=sleep,
        report=lambda a: None,
        until=at(14, 0),
    )
    log = history.recordings("SPY", store=tmp_path).to_pylist()
    assert [(r["scheduled_at"], r["status"]) for r in log] == [
        (at(13, 30), "empty"),
        (at(13, 45), "skipped"),
        (at(14, 0), "empty"),
    ]


def test_one_snapshot_reads_back_by_its_own_snapshot_at(gateway, tmp_path):
    first = live.option_chain("AAPL", strikes=(190, 200), max_dte=20)
    second = live.option_chain("AAPL", strikes=(190, 200), max_dte=20)
    history.record(first, store=tmp_path)
    history.record(second, store=tmp_path)
    assert first.snapshot_at is not None and first.snapshot_at != second.snapshot_at
    one = history.option_quotes(
        "AAPL", "2000-01-01", "2100-01-01", store=tmp_path, snapshot_at=first.snapshot_at
    )
    assert one.num_rows == first.rows
    assert set(one.column("snapshot_at").to_pylist()) == {first.snapshot_at}


def test_the_commands_record_once_and_list_the_log(gateway, tmp_path, capsys):
    args = ["--store", str(tmp_path), "record", "AAPL", "--strikes", "140,220", "--once"]
    assert main(args) == 0
    assert " ok " in capsys.readouterr().out
    assert main(["--store", str(tmp_path), "recordings", "AAPL"]) == 0
    assert "total    1 ok" in capsys.readouterr().out


def test_the_log_is_never_read_as_coverage(tmp_path):
    attempts.write(
        tmp_path, [attempts.Attempt(at(14), "ibkr", "option_quote", "SPY", attempts.OK, 5)]
    )
    with pytest.raises(ValueError, match="recorded, not fetched"):
        history.coverage("option_quote", "SPY", "2026-10-19", "2026-10-19", store=tmp_path)
