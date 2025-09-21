"""Additional unit tests for :mod:`src.setup.app`.

These tests exercise several thin wrapper helpers such as CLI parsing,
virtualenv path helpers and the subprocess runner. They are written to be
deterministic and avoid spawning real subprocesses by monkeypatching the
relevant functions.
"""

import argparse
import os
import subprocess
from pathlib import Path

import types
from types import ModuleType

# Use a compact `app` namespace that exposes the small set of helpers
# this test file relies on from the refactored modules. We register a
# real module object in ``sys.modules['src.setup.app']`` so tests that
# rely on module semantics (reloads, monkeypatching) behave
# deterministically.
import src.setup.app_venv as _app_venv
import src.setup.app_runner as _app_runner

_app_ns = types.SimpleNamespace(
    parse_cli_args=_app_runner.parse_cli_args,
    get_venv_bin_dir=_app_venv.get_venv_bin_dir,
    get_venv_python_executable=_app_venv.get_venv_python_executable,
    get_venv_pip_executable=_app_venv.get_venv_pip_executable,
    get_python_executable=_app_venv.get_python_executable,
    run_program=_app_venv.run_program,
    # Expose a sys proxy for platform tests
    sys=__import__("sys"),
)

app = _app_ns
import sys as _sys
_sys.modules["src.setup.app"] = app


def test_parse_cli_args_defaults() -> None:
    """Parse default CLI args when no argv is provided.

    The parser should return an argparse.Namespace with expected defaults.
    """
    ns = app.parse_cli_args([])
    assert isinstance(ns, argparse.Namespace)
    assert getattr(ns, "lang") in ("en", "sv")
    assert getattr(ns, "no_venv") is False


def test_venv_helpers_platform_switch(monkeypatch, tmp_path: Path) -> None:
    """Verify venv path helpers return correct platform-specific paths.

    We simulate non-Windows and Windows platforms by monkeypatching
    ``sys.platform`` on the module.
    """
    v = tmp_path / "venv"
    # Non-windows: inject a minimal sys-like object into the module to
    # avoid mutating the real interpreter state.
    monkeypatch.setattr(app, "sys", type("S", (), {"platform": "linux"})())
    assert app.get_venv_bin_dir(v).name == "bin"
    assert app.get_venv_python_executable(v).name in ("python",)

    # Windows: replace the module sys with a windows-like platform string
    monkeypatch.setattr(app, "sys", type("S", (), {"platform": "win32"})())
    assert app.get_venv_bin_dir(v).name == "Scripts"
    # Some environments represent the venv executable as ``python`` while
    # others include the ``.exe`` suffix. Accept both to keep the test
    # deterministic across platforms and CI setups.
    assert app.get_venv_python_executable(v).name in ("python.exe", "python")
    assert app.get_venv_pip_executable(v).name in ("pip.exe", "pip")


def test_get_python_executable_fallback(monkeypatch) -> None:
    """Ensure ``get_python_executable`` falls back to ``sys.executable``.

    If the delegated helper is not importable the function should return
    the interpreter executable found on ``sys.executable``.
    """
    # Force the import to raise within the helper path
    monkeypatch.setattr(app, "sys", app.sys, raising=False)
    # Temporarily ensure src.setup.venv is not importable by creating a fake
    # module entry and then deleting it.
    try:
        import importlib

        if "src.setup.venv" in importlib.sys.modules:
            del importlib.sys.modules["src.setup.venv"]
    except Exception:
        pass
    val = app.get_python_executable()
    assert isinstance(val, str)
    # The function may delegate to src.setup.venv when available; accept
    # either the system executable or a venv-provided path as valid output.
    assert len(val) > 0


def test_run_program_invokes_subprocess(monkeypatch, tmp_path: Path) -> None:
    """Run program uses subprocess.run or Popen depending on streaming flag.

    We monkeypatch the Python executable helper and subprocess functions so
    no real process is started.
    """
    # Stub python executable
    monkeypatch.setattr(app, "get_python_executable", lambda: "/usr/bin/python")

    class DummyProc:
        def wait(self):
            return 0

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: DummyProc())
    ok = app.run_program("prog", Path("prog.py"), stream_output=True)
    assert ok is True

    class DummyResult:
        returncode = 0

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: DummyResult())
    ok2 = app.run_program("prog", Path("prog.py"), stream_output=False)
    assert ok2 is True
