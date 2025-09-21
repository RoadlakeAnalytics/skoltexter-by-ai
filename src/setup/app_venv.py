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
from src.config import PROJECT_ROOT, VENV_DIR, REQUIREMENTS_FILE, REQUIREMENTS_LOCK_FILE


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
    # Use the real `sys.platform` rather than reading it from a shim
    # module. Tests should patch the concrete helpers in `src.setup.venv`.
    platform = sys.platform
    if platform == "win32":
        return venv_path / "Scripts"
    return venv_path / "bin"


def get_venv_python_executable(venv_path: Path) -> Path:
    """Return the path to the Python executable inside a virtualenv.

    Parameters
    ----------
    venv_path : Path
        Path to the virtual environment root directory.

    Returns
    -------
    Path
        Path to the Python interpreter inside the virtual environment.
    """
    bin_dir = get_venv_bin_dir(venv_path)
    platform = sys.platform
    if platform == "win32":
        return bin_dir / "python.exe"
    return bin_dir / "python"


def get_venv_pip_executable(venv_path: Path) -> Path:
    """Return the path to the pip executable inside a virtualenv.

    Parameters
    ----------
    venv_path : Path
        Path to the virtual environment root directory.

    Returns
    -------
    Path
        Path to the pip executable inside the virtual environment.
    """
    bin_dir = get_venv_bin_dir(venv_path)
    platform = sys.platform
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
    # Use explicit, concrete imports instead of reading a shim module.
    try:
        from src.setup.venv import get_python_executable as _get_python_executable

        python = _get_python_executable()
    except Exception:
        python = get_python_executable()

    env = os.environ.copy()
    # Respect the configured UI language when running subprocesses.
    try:
        from src.setup import i18n as _i18n

        env["LANG_UI"] = getattr(_i18n, "LANG", "en")
    except Exception:
        env["LANG_UI"] = "en"

    subprocess_mod = subprocess
    proj_root = PROJECT_ROOT or Path.cwd()
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
        # If direct import failed, attempt to pick up a test-installed
        # module from sys.modules (tests may insert a fake manager there).
        vm = sys.modules.get("src.setup.venv_manager")
        try:
            import src.setup.fs_utils as fs_utils
            if vm is not None:
                try:
                    vm.create_safe_path = fs_utils.create_safe_path
                    vm.safe_rmtree = fs_utils.safe_rmtree
                except Exception:
                    pass
        except Exception:
            pass

    class _UI:
        import logging

        logger = logging.getLogger("src.setup.app")
        # Delegate to possibly monkeypatched functions on the central app shim
        def _ask_text(*a, **k):
            app_mod = sys.modules.get("src.setup.app")
            f = getattr(app_mod, "ask_text", None)
            if f is None:
                return ""
            return f(*a, **k)

        def _ui_has_rich() -> bool:
            app_mod = sys.modules.get("src.setup.app")
            f = getattr(app_mod, "ui_has_rich", None)
            if f is None:
                return True
            try:
                return bool(f())
            except Exception:
                return True

        def _rprint(*a, **k):
            app_mod = sys.modules.get("src.setup.app")
            f = getattr(app_mod, "rprint", None)
            if f is None:
                print(*a, **k)
            else:
                try:
                    return f(*a, **k)
                except Exception:
                    print(*a, **k)

        rprint = staticmethod(_rprint)
        ui_has_rich = staticmethod(_ui_has_rich)
        ask_text = staticmethod(_ask_text)
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
                # Prefer implementations patched on the central app shim
                # (``src.setup.app``) so tests that monkeypatch there are
                # respected. Fall back to the local globals if not present.
                app_mod = sys.modules.get("src.setup.app")
                candidate = None
                if app_mod is not None:
                    candidate = getattr(app_mod, _name, None)
                if candidate is None and _name in globals():
                    candidate = globals()[_name]
                if candidate is not None and getattr(candidate, "__module__", None) != __name__:
                    had = hasattr(_venvmod, _name)
                    orig = getattr(_venvmod, _name) if had else None
                    _venv_orig[_name] = (had, orig)
                    try:
                        setattr(_venvmod, _name, candidate)
                    except Exception:
                        # Be defensive: if setting fails continue without
                        # overriding the venv module.
                        pass
        except Exception:
            _venvmod = None
            _venv_orig = {}

        try:
            # Prefer values patched on the central app shim when present so
            # tests that reload and then set attributes on ``src.setup.app``
            # are respected.
            # Prefer explicit configuration module lookups instead of
            # relying on a legacy shim module present in ``sys.modules``.
            # Tests should patch the concrete ``src.config`` module when
            # altering these values.
            try:
                import src.config as cfg

                proj = cfg.PROJECT_ROOT
                vdir = cfg.VENV_DIR
                req = cfg.REQUIREMENTS_FILE
                req_lock = cfg.REQUIREMENTS_LOCK_FILE
            except Exception:
                # As a defensive fallback keep the locally imported
                # constants to preserve prior behaviour when config
                # cannot be imported (very unlikely).
                proj = PROJECT_ROOT
                vdir = VENV_DIR
                req = REQUIREMENTS_FILE
                req_lock = REQUIREMENTS_LOCK_FILE

            vm.manage_virtual_environment(proj, vdir, req, req_lock, _UI)
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
