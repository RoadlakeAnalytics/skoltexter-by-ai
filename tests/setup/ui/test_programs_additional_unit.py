"""Additional tests for :mod:`src.setup.ui.programs`.

These focus on the TUI helpers that render program descriptions and
logs into a right-hand pane using the lightweight UI adapter.
"""

from pathlib import Path
import types

import src.setup.ui.programs as programs
from src.setup import console_helpers as ch


def test_view_program_descriptions_tui_renders_panel(monkeypatch):
    """The TUI variant should call the provided update_right callback with a Panel."""

    captured = []

    def update_right(obj):
        captured.append(obj)

    def update_prompt(obj):
        # not used in this test
        pass

    # Ensure we pick a known program id
    monkeypatch.setattr(programs, "get_program_descriptions", lambda: {"1": ("T", "BODY")})
    # Make the TUI prompt return '1' so a description is displayed
    monkeypatch.setattr(programs, "ask_text", lambda prompt: "1")

    programs._view_program_descriptions_tui(update_right, update_prompt)
    assert captured, "update_right should be called with a renderable"


def test_view_logs_tui_no_logs(monkeypatch, tmp_path: Path):
    """When LOG_DIR is empty the TUI should render a 'no logs' Panel."""

    # Point the module LOG_DIR at a temporary directory with no logs
    monkeypatch.setattr(programs, "LOG_DIR", tmp_path, raising=False)
    called = []

    def update_right(obj):
        called.append(obj)

    programs._view_logs_tui(update_right, lambda p: None)
    assert called, "Should render a panel even when no logs exist"


def test_view_logs_tui_with_file(monkeypatch, tmp_path: Path):
    """When a log file exists selecting it should display its contents."""

    # Create a fake log file
    (tmp_path / "a.log").write_text("line1\nline2\n")
    monkeypatch.setattr(programs, "LOG_DIR", tmp_path, raising=False)

    outputs = []

    def update_right(obj):
        outputs.append(obj)

    # Choose the first log file (index '1') then exit
    seq = ["1", "0"]

    def _ask(prompt=""):
        return seq.pop(0)

    monkeypatch.setattr(programs, "ask_text", _ask)
    programs._view_logs_tui(update_right, lambda p: None)
    assert outputs, "Should have rendered something for the selected log"

