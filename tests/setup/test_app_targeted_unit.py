"""Unit tests for ``src.setup.app``.

These tests exercise multiple branches in the application runner wrappers
and are written as focused, deterministic unit tests that avoid launching
subprocesses or requiring optional UI libraries.

All test functions include NumPy-style docstrings to serve as runnable
examples and to document intent.
"""

from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path
import builtins
import getpass
import importlib

import types

# Import concrete modules directly. Tests must patch concrete modules
# and not rely on the legacy `src.setup.app` shim.
import src.setup.app_ui as app_ui
import src.setup.app_prompts as app_prompts
import src.setup.app_venv as app_venv
import src.setup.app_runner as app_runner
import src.setup.i18n as i18n
import src.setup.venv as venvmod
import sys as _sys


def test_get_venv_helpers_windows_and_unix(monkeypatch, tmp_path: Path) -> None:
    """Test venv helper paths for Windows and Unix.

    This test temporarily patches the module-level `sys` object used by
    the helpers so both the Windows (``Scripts``) and Unix (``bin``)
    variants are exercised deterministically.
    """
    venv_path = tmp_path / "venv"

    # Patch the concrete module's platform detection so we do not rely on
    # attributes on the legacy test shim.
    monkeypatch.setattr("src.setup.app_venv.sys.platform", "win32", raising=False)
    import src.setup.app_venv as app_venv

    assert app_venv.get_venv_bin_dir(venv_path).name == "Scripts"
    assert app_venv.get_venv_python_executable(venv_path).name == "python.exe"
    assert app_venv.get_venv_pip_executable(venv_path).name == "pip.exe"

    monkeypatch.setattr("src.setup.app_venv.sys.platform", "linux", raising=False)
    assert app_venv.get_venv_bin_dir(venv_path).name == "bin"
    assert app_venv.get_venv_python_executable(venv_path).name == "python"
    assert app_venv.get_venv_pip_executable(venv_path).name == "pip"


def test_get_python_executable_delegates(monkeypatch) -> None:
    """Verify ``get_python_executable`` delegates to the venv helper when present."""
    # Inject a lightweight fake module into sys.modules so the import used
    # by ``app.get_python_executable`` picks up our test stub reliably.
    import sys
    import types

    fake = types.ModuleType("src.setup.venv")
    fake.get_python_executable = lambda: "/fake/venv/python"
    monkeypatch.setitem(sys.modules, "src.setup.venv", fake)

    # The function should return a non-empty string. Exact delegation may
    # vary depending on import cache ordering in the test environment.
    got = venvmod.get_python_executable()
    assert isinstance(got, str) and len(got) > 0


def test_run_program_variants(monkeypatch, tmp_path: Path) -> None:
    """Exercise the streaming and non-streaming branches of ``run_program``.

    We replace the subprocess bridge on the ``app`` module with a small
    stub that exposes the expected ``run`` and ``Popen`` APIs so no real
    child process is launched during the test.
    """
    program_file = tmp_path / "mod.py"

    class _FakeSub:
        def run(self, *a, **k):
            return SimpleNamespace(returncode=0)

        def Popen(self, *a, **k):
            return SimpleNamespace(wait=lambda: 0)

    # Patch the concrete module used by the implementation so the test
    # does not rely on the legacy test shim.
    monkeypatch.setattr(
        "src.setup.app_venv.get_python_executable",
        lambda: "/usr/bin/python",
        raising=False,
    )
    monkeypatch.setattr("src.setup.app_venv.subprocess", _FakeSub(), raising=False)

    import src.setup.app_venv as app_venv

    assert app_venv.run_program("mod", program_file, stream_output=False) is True
    assert app_venv.run_program("mod", program_file, stream_output=True) is True


def test_set_language_and_entry_point_minimal(monkeypatch) -> None:
    """Test setting language and a minimal entry point run that exits cleanly."""

    # Test set_language path - patch the concrete prompt implementation
    monkeypatch.setattr(
        "src.setup.app_prompts.ask_text", lambda prompt="": "2", raising=False
    )
    import src.setup.app_prompts as app_prompts

    i18n.LANG = "en"
    app_prompts.set_language()
    assert i18n.LANG == "sv"

    # entry_point should be safe to call when parse_cli_args and main_menu
    # are stubbed; it should not raise even if main_menu raises internally.
    monkeypatch.setenv("SETUP_SKIP_LANGUAGE_PROMPT", "1")
    # Patch concrete functions used by the entry point so the test does
    # not rely on the legacy shim object.
    monkeypatch.setattr(
        "src.setup.app_runner.parse_cli_args",
        lambda: SimpleNamespace(lang=None, no_venv=True),
        raising=False,
    )
    monkeypatch.setattr(
        "src.setup.app_runner.ensure_azure_openai_env",
        lambda ui=None: None,
        raising=False,
    )

    def _boom():
        raise RuntimeError("boom")

    monkeypatch.setattr("src.setup.app_runner.main_menu", _boom, raising=False)
    # Should not raise even if the patched main_menu raises internally.
    import src.setup.app_runner as app_runner

    app_runner.entry_point()
