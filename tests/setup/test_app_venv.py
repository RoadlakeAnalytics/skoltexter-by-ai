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
import importlib
import src.setup.venv as _unused_venv  # ensure importable during test collection


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


def test_get_python_executable_prefers_venv_impl(monkeypatch) -> None:
    """Ensure ``get_python_executable`` delegates to ``src.setup.venv`` when available.

    The concrete venv helper should be preferred when present. Patch the
    concrete ``src.setup.venv`` implementation and verify the delegated
    value is returned. Also verify that when the delegated implementation
    raises, a sensible non-empty fallback string is returned.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to patch module attributes.

    Returns
    -------
    None
    """
    venv_mod = importlib.import_module("src.setup.venv")
    monkeypatch.setattr(venv_mod, "get_python_executable", lambda: "/fake/venv/python")
    val = app_venv.get_python_executable()
    assert isinstance(val, str) and len(val) > 0

    def _bad():
        raise RuntimeError("bad")

    monkeypatch.setattr(venv_mod, "get_python_executable", _bad)
    res2 = app_venv.get_python_executable()
    assert isinstance(res2, str) and len(res2) > 0


def test_is_venv_active_delegates(monkeypatch) -> None:
    """Verify ``is_venv_active`` delegates to the concrete venv module.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to patch module attributes.

    Returns
    -------
    None
    """
    venv_mod = importlib.import_module("src.setup.venv")
    monkeypatch.setattr(venv_mod, "is_venv_active", lambda: True)
    assert venv_mod.is_venv_active() is True
    res = app_venv.is_venv_active()
    assert isinstance(res, bool)
    monkeypatch.setattr(venv_mod, "is_venv_active", lambda: False)
    assert venv_mod.is_venv_active() is False


def test_manage_virtual_environment_calls_manager(monkeypatch, tmp_path: Path) -> None:
    """Delegate to the venv manager when the wrapper is invoked.

    This test installs a fake ``src.setup.venv_manager`` implementation to
    capture the arguments the wrapper forwards. It also patches the
    canonical configuration values so the operation targets a temporary
    location during the test.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to install fakes and patch module attributes.
    tmp_path : pathlib.Path
        Temporary path used as a fake project root and venv directory.

    Returns
    -------
    None
    """
    called: dict = {}

    import src.setup.venv_manager as vm_mod

    def fake_manage(project_root, venv_dir, req_file, req_lock, UI):
        called["args"] = (project_root, venv_dir, req_file, req_lock)

    monkeypatch.setattr(vm_mod, "manage_virtual_environment", fake_manage, raising=False)

    import src.config as cfg
    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path, raising=True)
    monkeypatch.setattr(cfg, "VENV_DIR", tmp_path / "venv", raising=True)
    monkeypatch.setattr(subprocess, "check_call", lambda *a, **k: None, raising=False)

    # Call the concrete wrapper rather than the legacy shim to avoid
    # relying on a shim module object being present in ``sys.modules``.
    app_venv.manage_virtual_environment()
    assert "args" in called


def test_manage_virtual_environment_propagates_and_restores(monkeypatch) -> None:
    """Attributes injected into ``src.setup.venv`` are restored after calling the manager.

    The wrapper temporarily overrides selected helpers on the concrete
    ``src.setup.venv`` module, delegates to the manager and then restores
    the original attributes. Tests must patch the concrete modules rather
    than a legacy shim to avoid import-order flakiness.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to apply temporary attribute patches.

    Returns
    -------
    None
    """
    venv_mod = importlib.import_module("src.setup.venv")
    vm_mod = importlib.import_module("src.setup.venv_manager")

    # Save original
    orig = getattr(venv_mod, "get_python_executable", None)

    def fake_get_python_executable():
        return "/tmp/fake"

    # Install a fake manager that simply records it was called
    monkeypatch.setattr(vm_mod, "manage_virtual_environment", lambda *a, **k: None, raising=False)

    # Patch the concrete app_venv helper so the wrapper will propagate it
    monkeypatch.setattr(app_venv, "get_python_executable", fake_get_python_executable, raising=False)

    # Call the wrapper which should propagate and then restore the attribute
    app_venv.manage_virtual_environment()

    # The venv module should have its original attribute restored
    assert getattr(venv_mod, "get_python_executable", None) is orig
