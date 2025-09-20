"""Virtual environment helpers extracted from src.setup.app.

These wrappers provide small utilities for locating executables inside
virtualenvs and for invoking program subprocesses. They read test-modifiable
state from the primary ``src.setup.app`` module so tests can patch behaviour.
"""

from __future__ import annotations

import sys
import os
import subprocess
from pathlib import Path
from typing import Any


def get_venv_bin_dir(venv_path: Path) -> Path:
    """Return the venv bin/Scripts directory respecting patched `sys`.

    Parameters
    ----------
    venv_path : Path
        Path to the virtual environment root.

    Returns
    -------
    Path
        Path to the bin/Scripts directory inside the venv.
    """
    app_mod = sys.modules.get("src.setup.app")
    platform = getattr(getattr(app_mod, "sys", sys), "platform", "")
    if platform == "win32":
        return venv_path / "Scripts"
    return venv_path / "bin"


def get_venv_python_executable(venv_path: Path) -> Path:
    """Return the path to the Python executable inside a virtualenv."""
    bin_dir = get_venv_bin_dir(venv_path)
    platform = getattr(getattr(sys.modules.get("src.setup.app"), "sys", sys), "platform", "")
    if platform == "win32":
        return bin_dir / "python.exe"
    return bin_dir / "python"


def get_venv_pip_executable(venv_path: Path) -> Path:
    """Return the path to the pip executable inside a virtualenv."""
    bin_dir = get_venv_bin_dir(venv_path)
    platform = getattr(getattr(sys.modules.get("src.setup.app"), "sys", sys), "platform", "")
    if platform == "win32":
        return bin_dir / "pip.exe"
    return bin_dir / "pip"


def get_python_executable() -> str:
    """Return the Python executable for the current environment.

    Delegates to ``src.setup.venv.get_python_executable`` when available.
    """
    try:
        from src.setup.venv import get_python_executable as _g

        return _g()
    except Exception:
        return getattr(sys, "executable", "/usr/bin/python")


def is_venv_active() -> bool:
    """Return whether a Python virtual environment is currently active."""
    try:
        from src.setup.venv import is_venv_active as _impl

        return _impl()
    except Exception:
        return False


def run_program(program_name: str, program_file: Path, stream_output: bool = False) -> bool:
    """Run a program as a subprocess using the selected Python executable.

    This wrapper consults the app module for patched ``subprocess``/``sys``
    attributes so tests can inject fake behaviours.
    """
    app_mod = sys.modules.get("src.setup.app")
    python = getattr(app_mod, "get_python_executable", get_python_executable)()
    env = os.environ.copy()
    # Respect the configured UI language when running subprocesses
    env["LANG_UI"] = getattr(sys.modules.get("src.setup.app"), "LANG", "en")
    subprocess_mod = getattr(app_mod, "subprocess", subprocess)
    proj_root = getattr(sys.modules.get("src.setup.app"), "PROJECT_ROOT", Path.cwd())
    if stream_output:
        proc = subprocess_mod.Popen([python, "-m", program_file.with_suffix("").name], cwd=proj_root, env=env)
        return proc.wait() == 0
    result = subprocess_mod.run(
        [python, "-m", program_file.with_suffix("").name], cwd=proj_root, capture_output=True, text=True, env=env
    )
    return getattr(result, "returncode", 0) == 0


def manage_virtual_environment() -> None:
    """Invoke the refactored virtual environment manager.

    This wrapper prepares a lightweight UI adapter and synchronises a
    few helper functions so the venv manager can be exercised in tests
    without the full interactive runtime.
    """
    try:
        import src.setup.fs_utils as fs_utils
        import src.setup.venv_manager as vm

        vm.create_safe_path = fs_utils.create_safe_path
        vm.safe_rmtree = fs_utils.safe_rmtree
    except Exception:
        vm = None

    class _UI:
        import logging

        logger = logging.getLogger("src.setup.app")
        rprint = staticmethod(lambda *a, **k: None)
        ui_has_rich = staticmethod(lambda: True)
        ask_text = staticmethod(lambda *a, **k: "")
        subprocess = subprocess
        shutil = __import__("shutil")
        sys = sys
        venv = __import__("venv")
        os = os

        @staticmethod
        def _(k: str) -> str:
            return k

        ui_info = staticmethod(lambda *a, **k: None)
        ui_success = staticmethod(lambda *a, **k: None)
        ui_warning = staticmethod(lambda *a, **k: None)

    if vm is not None:
        _venvmod = None
        _venv_orig: dict[str, tuple[bool, object | None]] = {}
        try:
            import src.setup.venv as _venvmod

            for _name in (
                "is_venv_active",
                "get_venv_python_executable",
                "get_venv_pip_executable",
                "get_python_executable",
            ):
                if _name in globals():
                    _val = globals()[_name]
                    if getattr(_val, "__module__", None) != __name__:
                        had = hasattr(_venvmod, _name)
                        orig = getattr(_venvmod, _name) if had else None
                        _venv_orig[_name] = (had, orig)
                        setattr(_venvmod, _name, _val)
        except Exception:
            _venvmod = None
            _venv_orig = {}

        try:
            vm.manage_virtual_environment()
        finally:
            if _venvmod is not None:
                for _name, (had, orig) in _venv_orig.items():
                    if had:
                        setattr(_venvmod, _name, orig)
                    else:
                        if hasattr(_venvmod, _name):
                            try:
                                delattr(_venvmod, _name)
                            except Exception:
                                pass


__all__ = [
    "get_venv_bin_dir",
    "get_venv_python_executable",
    "get_venv_pip_executable",
    "get_python_executable",
    "is_venv_active",
    "run_program",
    "manage_virtual_environment",
]

