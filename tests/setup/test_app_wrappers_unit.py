"""Unit tests for lightweight wrappers in ``src.setup.app``.

These tests exercise the thin adapter functions that forward to the
refactored UI and venv helpers. External side-effects (subprocess, UI)
are stubbed using ``monkeypatch`` so tests remain deterministic.
"""

from pathlib import Path
import sys
import types
import importlib

# Import the refactored modules and expose a lightweight `app` namespace
# so existing tests can continue to call `app.<helper>` without depending
# on the legacy monolithic module.
import src.setup.app_ui as app_ui
import src.setup.app_prompts as app_prompts
import src.setup.app_venv as app_venv

app = types.SimpleNamespace(
    ui_rule=app_ui.ui_rule,
    ui_header=app_ui.ui_header,
    ui_info=app_ui.ui_info,
    ui_menu=app_ui.ui_menu,
    ask_text=app_prompts.ask_text,
    ask_confirm=app_prompts.ask_confirm,
    ask_select=app_prompts.ask_select,
    get_venv_bin_dir=app_venv.get_venv_bin_dir,
    get_python_executable=app_venv.get_python_executable,
    run_program=app_venv.run_program,
    # Expose the real sys module so tests can monkeypatch attributes on it.
    sys=sys,
)


def test_ui_wrappers_delegate(monkeypatch):
    """UI helper wrappers call into the UI backend without raising.

    We patch the implementation functions in ``src.setup.ui.basic`` so the
    app wrappers simply forward the call and we can assert no exceptions
    are raised.
    """
    calls = {}

    monkeypatch.setattr(
        "src.setup.ui.basic.ui_rule", lambda t: calls.setdefault("rule", t)
    )
    monkeypatch.setattr(
        "src.setup.ui.basic.ui_header", lambda t: calls.setdefault("header", t)
    )
    monkeypatch.setattr(
        "src.setup.ui.basic.ui_info", lambda m: calls.setdefault("info", m)
    )
    monkeypatch.setattr(
        "src.setup.ui.basic.ui_menu", lambda items: calls.setdefault("menu", items)
    )

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
    # Reload modules to ensure a clean state and then patch the prompts
    import importlib
    import src.setup.app as app_mod
    import src.setup.ui.prompts as prom_mod

    importlib.reload(prom_mod)
    importlib.reload(app_mod)

    monkeypatch.setattr(prom_mod, "ask_text", lambda p, default=None: "val")
    monkeypatch.setattr(prom_mod, "ask_confirm", lambda p, d=True: True)
    monkeypatch.setattr(prom_mod, "ask_select", lambda p, choices: choices[0])

    # Also patch the legacy top-level shim to avoid accidental interference
    try:
        import setup_project as sp_top

        monkeypatch.setattr(
            sp_top, "ask_text", lambda p, default=None: "val", raising=False
        )
    except Exception:
        # Not present in some environments: ignore
        pass
    # Ensure TUI mode is disabled on the reloaded app module so the wrapper
    # delegates to prompts.ask_text. Use the reloaded module object to avoid
    # order-dependent issues with previously-imported module objects.
    monkeypatch.setattr(app_mod, "_TUI_MODE", False, raising=False)
    monkeypatch.setattr(app_mod, "_TUI_UPDATER", None, raising=False)
    monkeypatch.setattr(app_mod, "_TUI_PROMPT_UPDATER", None, raising=False)
    # Also ensure orchestrator TUI flags are clear to avoid cross-module interference
    try:
        import src.setup.pipeline.orchestrator as orch

        monkeypatch.setattr(orch, "_TUI_MODE", False, raising=False)
        monkeypatch.setattr(orch, "_TUI_UPDATER", None, raising=False)
        monkeypatch.setattr(orch, "_TUI_PROMPT_UPDATER", None, raising=False)
    except Exception:
        pass

    assert app_mod.ask_text("p") == "val"
    assert app_mod.ask_confirm("p") is True
    assert app_mod.ask_select("p", ["A", "B"]) == "A"


def test_ask_text_tui_getpass(monkeypatch):
    """TUI path for ask_text uses getpass when TUI mode enabled."""
    import importlib

    # Import a fresh reference to the app module so we operate on the
    # module object currently registered in ``sys.modules``. Other
    # tests may replace the entry in ``sys.modules`` which would make a
    # previously-imported module object stale and cause
    # ``importlib.reload`` to raise an ImportError. Importing here
    # prevents order-dependent failures.
    app_mod = importlib.import_module("src.setup.app")
    importlib.reload(app_mod)
    monkeypatch.setattr(app_mod, "_TUI_MODE", True)
    monkeypatch.setattr(app_mod, "_TUI_UPDATER", lambda x: None)
    monkeypatch.setattr(app_mod, "_TUI_PROMPT_UPDATER", None)
    import getpass

    monkeypatch.setattr(getpass, "getpass", lambda prompt="": "secret")
    # Ensure input fallback is predictable if used
    import builtins

    monkeypatch.setattr(builtins, "input", lambda prompt="": "secret")
    val = app_mod.ask_text("prompt")
    assert val == "secret"
    # Reset TUI mode
    monkeypatch.setattr(app_mod, "_TUI_MODE", False)
    monkeypatch.setattr(app_mod, "_TUI_UPDATER", None)


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
