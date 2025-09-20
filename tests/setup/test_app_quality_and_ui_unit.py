"""Tests for app-level quality suite runners and UI helpers."""

import subprocess

import src.setup.app as app
from src import config as cfg


def test_run_full_and_extreme_quality_suites(monkeypatch, tmp_path):
    # Ensure subprocess.run is invoked but exceptions are swallowed
    calls = []

    def fake_run(cmd, cwd=None):
        calls.append((tuple(cmd), cwd))

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path, raising=False)
    app.run_full_quality_suite()
    app.run_extreme_quality_suite()
    assert calls, "subprocess.run was not called"


def test_app_ui_has_rich_and_rprint(monkeypatch, capsys):
    # Force console_helpers to report no rich
    import src.setup.console_helpers as ch

    monkeypatch.setattr(ch, "_RICH_CONSOLE", None)
    monkeypatch.setattr(ch, "ui_has_rich", lambda: False)
    # app.rprint should fall back to print
    app.rprint("x", "y")
    out = capsys.readouterr().out
    assert "x y" in out
