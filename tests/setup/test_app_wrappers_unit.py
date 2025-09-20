"""Unit tests for lightweight wrappers in ``src.setup.app``.

These tests exercise the thin adapter functions that forward to the
refactored UI and venv helpers. External side-effects (subprocess, UI)
are stubbed using ``monkeypatch`` so tests remain deterministic.
"""

from pathlib import Path
import sys

import src.setup.app as app


def test_ui_wrappers_delegate(monkeypatch):
    """UI helper wrappers call into the UI backend without raising.

    We patch the implementation functions in ``src.setup.ui.basic`` so the
    app wrappers simply forward the call and we can assert no exceptions
    are raised.
    """
    calls = {}

    monkeypatch.setattr("src.setup.ui.basic.ui_rule", lambda t: calls.setdefault("rule", t))
    monkeypatch.setattr("src.setup.ui.basic.ui_header", lambda t: calls.setdefault("header", t))
    monkeypatch.setattr("src.setup.ui.basic.ui_info", lambda m: calls.setdefault("info", m))
    monkeypatch.setattr("src.setup.ui.basic.ui_menu", lambda items: calls.setdefault("menu", items))

    app.ui_rule("T")
    app.ui_header("H")
    app.ui_info("I")
    app.ui_menu([(1, "A")])

    assert calls["rule"] == "T"
    assert calls["header"] == "H"
    assert calls["info"] == "I"
    assert calls["menu"] == [(1, "A")]


def test_prompt_wrappers_and_tty(monkeypatch):
    """ask_text/ask_confirm/ask_select delegate to prompts implementations.

    We stub the prompt functions to avoid interactive input.
    """
    monkeypatch.setattr("src.setup.ui.prompts.ask_text", lambda p, default=None: "val")
    monkeypatch.setattr("src.setup.ui.prompts.ask_confirm", lambda p, d=True: True)
    monkeypatch.setattr("src.setup.ui.prompts.ask_select", lambda p, choices: choices[0])

    # Also patch the legacy top-level shim to avoid accidental interference
    try:
        import setup_project as sp_top

        monkeypatch.setattr(sp_top, "ask_text", lambda p, default=None: "val", raising=False)
    except Exception:
        # Not present in some environments: ignore
        pass
    assert app.ask_text("p") == "val"
    assert app.ask_confirm("p") is True
    assert app.ask_select("p", ["A", "B"]) == "A"


def test_ask_text_tui_getpass(monkeypatch):
    """TUI path for ask_text uses getpass when TUI mode enabled."""
    monkeypatch.setattr(app, "_TUI_MODE", True)
    monkeypatch.setattr(app, "_TUI_UPDATER", lambda x: None)
    monkeypatch.setattr(app, "_TUI_PROMPT_UPDATER", None)
    import getpass

    monkeypatch.setattr(getpass, "getpass", lambda prompt="": "secret")
    val = app.ask_text("prompt")
    assert val == "secret"
    # Reset TUI mode
    monkeypatch.setattr(app, "_TUI_MODE", False)
    monkeypatch.setattr(app, "_TUI_UPDATER", None)


def test_venv_path_helpers_and_run_program(monkeypatch, tmp_path: Path):
    """Test venv helpers and run_program (stream and non-stream paths).

    We stub subprocess calls so no real processes are spawned.
    """
    v = tmp_path / "venv"
    # Non-windows
    monkeypatch.setattr(app, "sys", type("S", (), {"platform": "linux"})())
    assert app.get_venv_bin_dir(v).name in ("bin", "Scripts")

    # Test run_program non-stream
    monkeypatch.setattr(app, "get_python_executable", lambda: "/usr/bin/python")

    class R:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr("subprocess.run", lambda *a, **k: R())
    ok = app.run_program("p", Path("src/mod.py"), stream_output=False)
    assert ok is True

    # Test run_program streaming path with Popen stub
    class P:
        def wait(self):
            return 0

    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: P())
    ok = app.run_program("p", Path("src/mod.py"), stream_output=True)
    assert ok is True
