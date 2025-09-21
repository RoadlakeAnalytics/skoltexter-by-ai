import builtins
import sys
from pathlib import Path
from types import SimpleNamespace

"""Unit tests for top-level `setup_project.py` helpers.

These tests exercise many branches of the setup script by monkeypatching
external dependencies and user input functions. They avoid performing
destructive operations by stubbing subprocess and filesystem calls.
"""


import importlib
import pytest

# Import the module object for the legacy top-level name so reloads and
# other import-time tests behave deterministically. Map commonly used
# attributes from the refactored modules onto the module to reduce
# dependency on the old monolith while keeping tests stable during
# migration.
sp = importlib.import_module("src.setup.app")
import src.setup.app_ui as app_ui
import src.setup.app_prompts as app_prompts
import src.setup.app_venv as app_venv
import src.setup.app_runner as app_runner
import src.setup.app_pipeline as app_pipeline
import src.setup.azure_env as azure_env

setattr(sp, "ui_rule", app_ui.ui_rule)
setattr(sp, "ui_header", app_ui.ui_header)
setattr(sp, "ui_status", app_ui.ui_status)
setattr(sp, "ui_info", app_ui.ui_info)
setattr(sp, "ui_success", app_ui.ui_success)
setattr(sp, "ui_warning", app_ui.ui_warning)
setattr(sp, "ui_error", app_ui.ui_error)
setattr(sp, "ui_menu", app_ui.ui_menu)

setattr(sp, "ask_text", app_prompts.ask_text)
setattr(sp, "ask_confirm", app_prompts.ask_confirm)
setattr(sp, "ask_select", app_prompts.ask_select)
setattr(sp, "prompt_virtual_environment_choice", app_prompts.prompt_virtual_environment_choice)

setattr(sp, "get_venv_bin_dir", app_venv.get_venv_bin_dir)
setattr(sp, "get_python_executable", app_venv.get_python_executable)

setattr(sp, "parse_cli_args", app_runner.parse_cli_args)
setattr(sp, "parse_env_file", app_runner.parse_env_file)
setattr(sp, "prompt_and_update_env", app_runner.prompt_and_update_env)
setattr(sp, "ensure_azure_openai_env", app_runner.ensure_azure_openai_env)
setattr(sp, "run_ai_connectivity_check_silent", app_runner.run_ai_connectivity_check_silent)
setattr(sp, "entry_point", app_runner.entry_point)
setattr(sp, "main_menu", app_runner.main_menu)
setattr(sp, "find_missing_env_keys", app_runner.find_missing_env_keys)
setattr(sp, "REQUIRED_AZURE_KEYS", getattr(azure_env, "REQUIRED_AZURE_KEYS", []))

setattr(sp, "_run_processing_pipeline_plain", app_pipeline._run_processing_pipeline_plain)
setattr(sp, "_run_processing_pipeline_rich", app_pipeline._run_processing_pipeline_rich)


def test_ui_helpers_fallback(capsys, monkeypatch):
    """Exercise UI fallback helpers when rich console is not available.

    Parameters
    ----------
    capsys : pytest.CaptureFixture
        Fixture to capture stdout/stderr.
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching module-level state.

    Returns
    -------
    None
    """
    # Force non-rich code path
    monkeypatch.setattr(sp, "_RICH_CONSOLE", None)
    sp.ui_rule("Title")
    sp.ui_header("Header")
    with sp.ui_status("Working..."):
        pass
    sp.ui_info("info")
    sp.ui_success("ok")
    sp.ui_warning("warn")
    sp.ui_error("err")
    sp.ui_menu([("1", "A"), ("2", "B")])
    out = capsys.readouterr().out
    assert "Title" in out or "Header" in out


def test_ask_helpers_branches(monkeypatch):
    """Verify the ask_text wrapper forwards to the prompts adapter or input.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching module-level state.

    Returns
    -------
    None
    """
    # Ensure the module is in a clean state (reload restores originals)
    import importlib
    import sys

    # Ensure the imported module object is present in sys.modules so
    # importlib.reload() behaves deterministically even if prior tests
    # manipulated sys.modules.
    # Import afresh to avoid issues where different module objects exist
    # under the same name in sys.modules due to prior test manipulation.
    sp = importlib.import_module("src.setup.app")
    importlib.reload(sp)

    # Fallback input
    monkeypatch.setattr(builtins, "input", lambda prompt="": "hello")
    monkeypatch.setattr(sp, "_TUI_MODE", False)
    monkeypatch.setattr(sp, "_HAS_Q", False)
    assert sp.ask_text("prompt:") == "hello"

    # Questionary path
    # Simulate the prompts module returning a questionary answer so the
    # app wrapper forwards correctly to the prompts implementation.
    import importlib as _il

    _prom = _il.import_module("src.setup.ui.prompts")
    monkeypatch.setattr(_prom, "ask_text", lambda p, default=None: "qval")
    assert sp.ask_text("p") == "qval"

    # Note: TUI getpass branches are tested in a dedicated test to avoid
    # interference with the questionary-specific branch tested above.


def test_venv_path_helpers(monkeypatch, tmp_path: Path):
    """Verify virtualenv bin directory selection for different platforms.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching module-level attributes.
    tmp_path : Path
        Temporary path used as the virtualenv root.

    Returns
    -------
    None
    """
    v = tmp_path / "venv"
    # Patch the concrete venv helper module `sys` so the function under
    # test reads the expected platform value from its own module globals.
    monkeypatch.setattr("src.setup.app_venv.sys", SimpleNamespace(platform="linux"), raising=False)
    assert sp.get_venv_bin_dir(v).name in ("bin", "Scripts")
    monkeypatch.setattr("src.setup.app_venv.sys", SimpleNamespace(platform="win32"), raising=False)
    assert sp.get_venv_bin_dir(v).name == "Scripts"


def test_translate_and_alias(monkeypatch):
    """Test translation function and unknown key fallback behavior.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching module-level values.

    Returns
    -------
    None
    """
    monkeypatch.setattr(sp, "LANG", "en")
    assert isinstance(sp.translate("welcome"), str)
    # Unknown key returns key
    assert sp.translate("no_such_key") == "no_such_key"


def test_set_language_and_exit(monkeypatch):
    """Verify language selection flow and exit behavior on interrupt.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching input behaviour.

    Returns
    -------
    None
    """
    # This test has been consolidated into the canonical
    # `tests/setup/test_app_prompts.py` and removed from this file.














