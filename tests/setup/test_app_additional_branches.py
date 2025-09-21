"""Additional unit tests for ``src.setup.app`` wrappers and helpers.

Tests focus on lightweight wrappers (UI delegation), venv helper
resolution and small utility behaviour that can be asserted
deterministically without starting subprocesses or modifying the
developer's environment.

"""

from types import SimpleNamespace
from pathlib import Path
import sys as _sys
import types

import src.setup.app_ui as _app_ui
import src.setup.app_prompts as _app_prompts
import src.setup.app_venv as _app_venv
import src.setup.app_runner as _app_runner
import src.setup.i18n as i18n

_app_ns = types.SimpleNamespace(
    parse_cli_args=_app_runner.parse_cli_args,
    _sync_console_helpers=_app_ui._sync_console_helpers,
    _RICH_CONSOLE=None,
    _HAS_Q=False,
    questionary=None,
    ui_rule=_app_ui.ui_rule,
    ui_header=_app_ui.ui_header,
    ui_info=_app_ui.ui_info,
    ui_warning=_app_ui.ui_warning,
    ui_success=_app_ui.ui_success,
    get_venv_bin_dir=_app_venv.get_venv_bin_dir,
    get_venv_python_executable=_app_venv.get_venv_python_executable,
    get_venv_pip_executable=_app_venv.get_venv_pip_executable,
    run_program=_app_venv.run_program,
    ask_text=_app_prompts.ask_text if hasattr(_app_prompts, "ask_text") else None,
    prompt_virtual_environment_choice=(
        _app_prompts.prompt_virtual_environment_choice
        if hasattr(_app_prompts, "prompt_virtual_environment_choice")
        else None
    ),
    set_language=(
        _app_prompts.set_language if hasattr(_app_prompts, "set_language") else None
    ),
    subprocess=__import__("subprocess"),
)

app = _app_ns
import sys as _sys

_sys.modules["src.setup.app"] = app


def test_parse_cli_args_and_sync_console_helpers(monkeypatch) -> None:
    """CLI parsing returns expected attributes and sync pushes to console_helpers.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to patch module attributes.

    Returns
    -------
    None
    """
    args = app.parse_cli_args(["--lang", "sv", "--no-venv", "--ui", "textual"])
    assert args.lang == "sv" and args.no_venv is True and args.ui == "textual"

    # Test _sync_console_helpers propagates test toggles
    monkeypatch.setattr(app, "_RICH_CONSOLE", "RC", raising=False)
    monkeypatch.setattr(app, "_HAS_Q", True, raising=False)
    monkeypatch.setattr(
        app, "questionary", SimpleNamespace(text=lambda *a, **k: None), raising=False
    )
    # Call and ensure no exception (propagation happens into console_helpers)
    app._sync_console_helpers()


def test_ui_wrappers_delegate(monkeypatch) -> None:
    """UI wrapper functions delegate to the underlying UI implementations.

    We patch the underlying implementations in ``src.setup.ui.basic`` and
    assert that the thin wrappers in this module call them.
    """
    called = {}

    monkeypatch.setattr(app, "_sync_console_helpers", lambda: None, raising=False)
    monkeypatch.setattr(
        "src.setup.ui.basic.ui_rule",
        lambda t: called.setdefault("rule", t),
        raising=False,
    )
    monkeypatch.setattr(
        "src.setup.ui.basic.ui_header",
        lambda t: called.setdefault("header", t),
        raising=False,
    )
    monkeypatch.setattr(
        "src.setup.ui.basic.ui_info",
        lambda m: called.setdefault("info", m),
        raising=False,
    )
    monkeypatch.setattr(
        "src.setup.ui.basic.ui_warning",
        lambda m: called.setdefault("warn", m),
        raising=False,
    )
    monkeypatch.setattr(
        "src.setup.ui.basic.ui_success",
        lambda m: called.setdefault("succ", m),
        raising=False,
    )

    app.ui_rule("T")
    app.ui_header("H")
    app.ui_info("I")
    app.ui_warning("W")
    app.ui_success("S")

    assert called["rule"] == "T"
    assert called["header"] == "H"
    assert called["info"] == "I"
    assert called["warn"] == "W"
    assert called["succ"] == "S"


# The venv-related tests were migrated to
# ``tests/setup/test_app_venv.py`` and removed from this file.


def test_run_program_subprocess_and_stream(monkeypatch, tmp_path: Path) -> None:
    """run_program uses subprocess.run and Popen depending on stream_output.

    We stub Popen and run to avoid spawning real processes.
    """
    monkeypatch.setattr(app, "get_python_executable", lambda: "python", raising=False)

    class FakeProc:
        def wait(self):
            return 0

    monkeypatch.setattr(
        app.subprocess, "Popen", lambda *a, **k: FakeProc(), raising=False
    )
    # For stream_output True
    assert app.run_program("m", Path("mod.py"), stream_output=True) is True

    class FakeRes:
        returncode = 0

    monkeypatch.setattr(app.subprocess, "run", lambda *a, **k: FakeRes(), raising=False)
    assert app.run_program("m", Path("mod.py"), stream_output=False) is True


def test_prompt_virtual_environment_choice_and_set_language(monkeypatch) -> None:
    """Prompt for virtual env choice and set_language behaviour.

    The functions are small and deterministic when provided with
    controlled responses from ``ask_text``.
    """
    # Virtual env choice -> '1' returns True (patch concrete prompt)
    monkeypatch.setattr("src.setup.app_prompts.ask_text", lambda prompt: "1")
    assert app.prompt_virtual_environment_choice() is True
    # Virtual env choice -> '2' returns False and ui_info called
    monkeypatch.setattr("src.setup.app_prompts.ask_text", lambda prompt: "2")
    monkeypatch.setattr("src.setup.app_ui.ui_info", lambda m: None)
    assert app.prompt_virtual_environment_choice() is False

    # set_language: choose '1' and '2' (patch concrete prompt implementation)
    monkeypatch.setattr("src.setup.app_prompts.ask_text", lambda prompt: "1")
    app.set_language()
    assert i18n.LANG == "en"
    monkeypatch.setattr("src.setup.app_prompts.ask_text", lambda prompt: "2")
    app.set_language()
    assert i18n.LANG == "sv"
