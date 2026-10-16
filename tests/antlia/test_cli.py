"""`antlia` -- the dispatcher in front of each area's own CLI."""

from __future__ import annotations

import subprocess
import sys
import types

import pytest

from antlia import cli


def test_importing_the_dispatcher_imports_no_area():
    # `antlia auth` must not pay for the query engine, so no area is imported
    # until it is chosen.
    out = subprocess.run(
        [
            sys.executable,
            "-c",
            "import antlia.cli, sys;"
            "print(sorted(m for m in sys.modules if m.startswith('antlia.')))",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert out.strip() == "['antlia.cli']"


@pytest.mark.parametrize("argv", [[], ["-h"], ["--help"]])
def test_no_area_prints_every_area(argv, capsys):
    assert cli.main(argv) == 0
    out = capsys.readouterr().out
    for area in cli.AREAS:
        assert area.name in out


def test_an_unknown_area_is_a_usage_error(capsys):
    assert cli.main(["acount"]) == 2
    err = capsys.readouterr().err
    assert "'acount'" in err and "history" in err


def test_the_rest_of_the_line_reaches_the_area_unchanged(monkeypatch):
    seen: list[list[str]] = []
    fake = types.ModuleType("fake_area")

    def main(argv: list[str]) -> int:
        seen.append(argv)
        return 7

    fake.main = main  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "fake_area", fake)
    monkeypatch.setattr(cli, "AREAS", (cli.Area("fake", "fake_area", "a test area"),))
    assert cli.main(["fake", "-p", "paper", "--verify", "-h"]) == 7
    assert seen == [["-p", "paper", "--verify", "-h"]]


def test_every_area_has_a_main():
    import importlib

    for area in cli.AREAS:
        assert callable(importlib.import_module(area.module).main), area.module
