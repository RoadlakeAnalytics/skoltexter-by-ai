"""Canonical tests for the ``src.setup.app_venv`` production module.

These tests exercise the virtual-environment helpers and the subprocess
runner in the concrete module. They patch the concrete module
(``src.setup.app_venv``) directly instead of relying on the legacy
``src.setup.app`` shim.

"""

from types import SimpleNamespace
from pathlib import Path
import importlib
import subprocess

import src.setup.app_venv as app_venv


def test_get_venv_bin_dir_and_executables(monkeypatch, tmp_path: Path) -> None:
    """Return platform-specific virtualenv paths and executables.

    This test patches the concrete ``src.setup.app_venv`` module's
    ``sys`` reference so the helpers behave as if running on different
    platforms. The tests assert exact names to keep behaviour explicit.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to patch module attributes.
    tmp_path : pathlib.Path
        Temporary filesystem path provided by pytest.

    Returns
    -------
    None
    """
    v = tmp_path / "venv"

    # Non-Windows
    monkeypatch.setattr(app_venv, "sys", SimpleNamespace(platform="linux"), raising=False)
    assert app_venv.get_venv_bin_dir(v).name == "bin"
    assert app_venv.get_venv_python_executable(v).name == "python"
    assert app_venv.get_venv_pip_executable(v).name == "pip"

    # Windows
    monkeypatch.setattr(app_venv, "sys", SimpleNamespace(platform="win32"), raising=False)
    assert app_venv.get_venv_bin_dir(v).name == "Scripts"
    assert app_venv.get_venv_python_executable(v).name == "python.exe"
    assert app_venv.get_venv_pip_executable(v).name == "pip.exe"


def test_get_python_executable_fallback(monkeypatch) -> None:
    """Ensure ``get_python_executable`` returns a sensible string when helper is missing.

    The concrete helper attempts to import ``src.setup.venv``; remove any
    cached module to force the fallback path.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to patch module attributes.

    Returns
    -------
    None
    """
    modsys = importlib.sys
    saved = None
    if "src.setup.venv" in modsys.modules:
        saved = modsys.modules.pop("src.setup.venv")
    try:
        val = app_venv.get_python_executable()
        assert isinstance(val, str) and len(val) > 0
    finally:
        if saved is not None:
            modsys.modules["src.setup.venv"] = saved


def test_run_program_invokes_subprocess(monkeypatch, tmp_path: Path) -> None:
    """Run program uses subprocess.Popen or subprocess.run depending on stream flag.

    We patch the concrete python-executable helper and the ``subprocess``
    functions so no real process is spawned.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to patch module attributes.
    tmp_path : pathlib.Path
        Temporary filesystem path provided by pytest.

    Returns
    -------
    None
    """
    monkeypatch.setattr(app_venv, "get_python_executable", lambda: "/usr/bin/python", raising=False)

    class DummyProc:
        def wait(self):
            return 0

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: DummyProc(), raising=False)
    ok = app_venv.run_program("prog", Path("prog.py"), stream_output=True)
    assert ok is True

    class DummyResult:
        returncode = 0

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: DummyResult(), raising=False)
    ok2 = app_venv.run_program("prog", Path("prog.py"), stream_output=False)
    assert ok2 is True

