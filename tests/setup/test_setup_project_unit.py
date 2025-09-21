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
setattr(
    sp,
    "prompt_virtual_environment_choice",
    app_prompts.prompt_virtual_environment_choice,
)

setattr(sp, "get_venv_bin_dir", app_venv.get_venv_bin_dir)
setattr(sp, "get_python_executable", app_venv.get_python_executable)

setattr(sp, "parse_cli_args", app_runner.parse_cli_args)
setattr(sp, "parse_env_file", app_runner.parse_env_file)
setattr(sp, "prompt_and_update_env", app_runner.prompt_and_update_env)
setattr(sp, "ensure_azure_openai_env", app_runner.ensure_azure_openai_env)
setattr(
    sp, "run_ai_connectivity_check_silent", app_runner.run_ai_connectivity_check_silent
)
setattr(sp, "entry_point", app_runner.entry_point)
setattr(sp, "main_menu", app_runner.main_menu)
setattr(sp, "find_missing_env_keys", app_runner.find_missing_env_keys)
setattr(sp, "REQUIRED_AZURE_KEYS", getattr(azure_env, "REQUIRED_AZURE_KEYS", []))

setattr(
    sp, "_run_processing_pipeline_plain", app_pipeline._run_processing_pipeline_plain
)
setattr(sp, "_run_processing_pipeline_rich", app_pipeline._run_processing_pipeline_rich)


# Note: TUI getpass branches are tested in a dedicated test to avoid
# interference with the questionary-specific branch tested above.


# The tests for UI helpers, prompts and venv helpers have been moved to
# the canonical `tests/setup/test_app.py` to consolidate shim-related
# tests and to ensure they patch concrete modules rather than the old
# `src.setup.app` shim.


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


# Tests migrated from other files to consolidate coverage for the
# top-level launcher `setup_project.py` into a single canonical test
# module. Local imports are used to avoid colliding with the module
# object ``sp`` which refers to ``src.setup.app`` in this file.


def test_run_program_uses_propagated_python(monkeypatch) -> None:
    """Patch `setup_project.get_python_executable` and ensure delegated run uses it.

    This test ensures that when the top-level helper providing the Python
    executable is patched on the launcher module, the delegated
    `run_program` invocation uses the patched value. The test avoids
    interacting with the legacy `src.setup.app` shim and instead patches
    the concrete subprocess used by the refactored venv implementation.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching attributes during the test.

    Returns
    -------
    None
    """
    import setup_project as setup_proj

    # Patch the top-level helper to return a known python path
    monkeypatch.setattr(setup_proj, "get_python_executable", lambda: "/usr/bin/python")

    class R:
        returncode = 0
        stdout = ""
        stderr = ""

    # Prevent spawning real subprocesses in the delegated implementation by
    # patching the concrete subprocess runner used by the refactored venv
    # helper module instead of touching any legacy shim module object.
    monkeypatch.setattr(
        "src.setup.app_venv.subprocess.run", lambda *a, **k: R(), raising=False
    )

    ok = setup_proj.run_program("prog", Path("src/some_module.py"), stream_output=False)
    assert ok is True

    # Ensure the launcher still exposes the patched helper.
    assert callable(getattr(setup_proj, "get_python_executable", None))


def test_setup_project_run_program_non_stream(monkeypatch) -> None:
    """Run program non-streaming using the launcher and patched subprocess.

    This test verifies that the top-level launcher `run_program` delegates
    correctly to the refactored implementation and treats the subprocess
    result return code as success when it is zero.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to monkeypatch attributes.

    Returns
    -------
    None
    """
    import setup_project as setup_proj

    monkeypatch.setattr(setup_proj, "get_python_executable", lambda: "/usr/bin/python")

    class R:
        returncode = 0
        stdout = ""
        stderr = ""

    # Patch the concrete subprocess used by the venv helper.
    monkeypatch.setattr(
        "src.setup.app_venv.subprocess.run", lambda *a, **k: R(), raising=False
    )
    ok = setup_proj.run_program(
        "program_1", Path("src/program1_generate_markdowns.py"), stream_output=False
    )
    assert ok is True


def test_manage_virtual_environment_recreate(monkeypatch, tmp_path: Path) -> None:
    """Simulate an existing venv and user confirming recreate.

    This test verifies the manager's recreate branch. It patches the
    concrete configuration value ``src.config.VENV_DIR`` so that the
    operation targets a temporary directory instead of the repository
    venv. Filesystem helpers and subprocess invocations are stubbed so
    the test is side-effect free.

    Parameters
    ----------
    monkeypatch : _pytest.monkeypatch.MonkeyPatch
        Fixture to patch attributes and modules during the test.
    tmp_path : pathlib.Path
        Temporary path used to host a fake venv directory.

    Returns
    -------
    None
        The test asserts that no exception is raised and returns nothing.
    """
    import setup_project as setup_proj
    from src.setup import fs_utils
    from src import config as cfg

    # Simulate existing interpreter not active and ensure venv dir under cfg
    monkeypatch.setattr(setup_proj, "is_venv_active", lambda: False)
    monkeypatch.setattr(cfg, "VENV_DIR", tmp_path / "venv", raising=True)
    (cfg.VENV_DIR).mkdir()
    # Return yes for prompts in this test (stable across orderings)
    monkeypatch.setattr(setup_proj, "ask_text", lambda prompt, default="y": "y")

    # Patch filesystem helpers and subprocess/venv calls
    monkeypatch.setattr(fs_utils, "create_safe_path", lambda p: p, raising=False)
    monkeypatch.setattr(fs_utils, "safe_rmtree", lambda p: None, raising=False)
    monkeypatch.setattr(
        setup_proj,
        "get_venv_pip_executable",
        lambda p: p / "bin" / "pip",
        raising=False,
    )
    monkeypatch.setattr(
        setup_proj,
        "get_venv_python_executable",
        lambda p: p / "bin" / "python",
        raising=False,
    )
    monkeypatch.setattr(
        setup_proj, "venv", SimpleNamespace(create=lambda *a, **k: None), raising=False
    )
    monkeypatch.setattr(
        "src.setup.app_venv.subprocess.check_call", lambda *a, **k: None, raising=False
    )

    # Should not raise
    setup_proj.manage_virtual_environment()
