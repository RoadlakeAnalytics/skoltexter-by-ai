"""Tests for programs and menu UI paths (non-interactive branches).

These tests use temporary log directories and simple stubs for input so
the interactive loops exit immediately.
"""

from pathlib import Path
import types

import src.setup.ui.programs as programs
import src.setup.ui.menu as menu


def test_get_program_descriptions():
    desc = programs.get_program_descriptions()
    assert set(desc.keys()) == {"1", "2", "3"}


def test_view_program_descriptions_prints(monkeypatch, capsys):
    # Force non-rich branch
    monkeypatch.setattr(programs, 'ui_has_rich', lambda: False)
    # Simulate choosing program 1 then 0 to exit
    seq = iter(["1", "0"])
    monkeypatch.setattr(programs, 'ask_text', lambda prompt: next(seq))
    printed = []
    monkeypatch.setattr(programs, 'rprint', lambda v: printed.append(v))
    programs.view_program_descriptions()
    # Expect either the raw body or some markdown-like text
    assert printed


def test_view_logs_plain(monkeypatch, tmp_path: Path):
    # Create a fake log directory with one log file
    logdir = tmp_path / "logs"
    logdir.mkdir()
    f = logdir / "a.log"
    f.write_text("line1\nline2")
    monkeypatch.setattr(programs, 'LOG_DIR', logdir)
    # Ask to view the first file and then exit
    seq = iter(["1", "0"])
    monkeypatch.setattr(programs, 'ask_text', lambda prompt: next(seq))
    captured = []
    monkeypatch.setattr(programs, 'rprint', lambda v: captured.append(v))
    programs.view_logs()
    # The rendered output should include the filename we created.
    assert any("a.log" in str(x) for x in captured)


def test_ui_main_menu_plain_exit(monkeypatch):
    # Force non-rich main menu and exit immediately
    monkeypatch.setattr(menu, 'ui_has_rich', lambda: False)
    monkeypatch.setattr(menu, 'ask_text', lambda prompt: '6')
    # Make sure functions referenced by the menu are no-ops
    monkeypatch.setattr(menu, '_manage_env', lambda: None)
    monkeypatch.setattr(menu, 'view_program_descriptions', lambda: None)
    monkeypatch.setattr(menu, 'run_processing_pipeline', lambda: None)
    monkeypatch.setattr(menu, 'view_logs', lambda: None)
    monkeypatch.setattr(menu, 'reset_project', lambda: None)
    # Should return without raising
    menu.main_menu()
