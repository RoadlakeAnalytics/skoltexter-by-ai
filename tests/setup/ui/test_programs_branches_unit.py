"""Unit tests for :mod:`src.setup.ui.programs` covering descriptions and logs.

Tests are deterministic by monkeypatching `ask_text`, `rprint` and the
`LOG_DIR` location so no actual TUI or filesystem state outside the test
directory is required.
"""

from pathlib import Path
import importlib

import src.setup.ui.programs as programs


def test_get_program_descriptions_keys():
    """get_program_descriptions returns a mapping for three programs.

    The returned mapping should contain keys "1", "2", "3" with
    two-tuple values describing each program.
    """
    desc = programs.get_program_descriptions()
    assert set(desc.keys()) == {"1", "2", "3"}
    for v in desc.values():
        assert isinstance(v, tuple) and len(v) == 2


def test__view_program_descriptions_tui_update_right(monkeypatch):
    """The TUI variant should call the provided `update_right` callback.

    We stub `ask_text` to choose an existing program and ensure
    `update_right` receives a Panel-like object.
    """
    calls = {}

    def update_right(obj):
        calls.setdefault("last", obj)

    monkeypatch.setattr(programs, "ask_text", lambda prompt: "1")
    programs._view_program_descriptions_tui(update_right, lambda p: None)
    assert "last" in calls


def test__view_logs_tui_no_logs(monkeypatch, tmp_path: Path):
    """If `LOG_DIR` has no logs the updater should receive a no-logs Panel."""
    # Point module LOG_DIR to an empty temporary directory
    monkeypatch.setattr(programs, "LOG_DIR", tmp_path)
    got = {}

    def update_right(obj):
        got["obj"] = obj

    programs._view_logs_tui(update_right, lambda p: None)
    assert "obj" in got


def test_view_logs_displays_existing_log(monkeypatch, tmp_path: Path):
    """When a log exists `view_logs` should rprint its content.

    We create a simple `.log` file and simulate asking for its index;
    the function should print the file contents via `rprint`.
    """
    # Create a log file
    d = tmp_path / "logs"
    d.mkdir()
    f = d / "a.log"
    f.write_text("line1\nline2")

    monkeypatch.setattr(programs, "LOG_DIR", d)
    # Stub ask_text to select the first entry then exit
    seq = ["1", "0"]
    monkeypatch.setattr(programs, "ask_text", lambda prompt: seq.pop(0))

    printed = []

    def fake_rprint(*args, **kwargs):
        printed.append(" ".join(str(a) for a in args))

    monkeypatch.setattr(programs, "rprint", fake_rprint)
    # Force non-rich code path so the raw content is passed to our fake_rprint
    monkeypatch.setattr(programs, "ui_has_rich", lambda: False)
    programs.view_logs()
    # Expect the file content to appear in the captured prints
    assert any("line1" in p or "line2" in p for p in printed)
