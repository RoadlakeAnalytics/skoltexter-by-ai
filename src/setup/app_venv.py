"""Virtual environment helpers for setup and subprocess invocation.

Utilities for locating virtual environment executables and for invoking
subprocesses using the appropriate interpreter. Functions are cross‑platform
and intended for use by setup and orchestration code.

Examples
--------
>>> from src.setup.app_venv import get_venv_python_executable
>>> from pathlib import Path
>>> ve = get_venv_python_executable(Path("/tmp/myvenv"))
>>> assert ve.name.startswith("python")
>>> from src.setup.app_venv import get_venv_bin_dir
>>> assert get_venv_bin_dir(Path("/tmp/myvenv")).name in ("bin", "Scripts")

"""

from __future__ import annotations

import sys
import os
import subprocess
from pathlib import Path
from typing import Any, Optional
from types import ModuleType
from src.config import PROJECT_ROOT, VENV_DIR, REQUIREMENTS_FILE, REQUIREMENTS_LOCK_FILE


def get_venv_bin_dir(venv_path: Path) -> Path:
    r"""Get the bin or Scripts directory path within a Python virtual environment.

    Determines the correct directory for virtual environment executables: 'bin' for POSIX platforms,
    'Scripts' for Windows. This abstraction enables reliable subprocess invocation and robust
    cross-platform testing/operation.

    Parameters
    ----------
    venv_path : Path
        Path to the virtual environment root directory.

    Returns
    -------
    Path
        Path to the bin (POSIX) or Scripts (Windows) subdirectory inside the venv.

    Raises
    ------
    None

    See Also
    --------
    get_venv_python_executable : Get the Python interpreter path in a venv.
    get_venv_pip_executable : Get the pip executable path in a venv.

    Notes
    -----
    Tests may patch helpers in ``src.setup.venv`` to control platform branches
    in unit tests. This function always returns a Path and does not raise.

    Examples
    --------
    >>> from pathlib import Path
    >>> get_venv_bin_dir(Path("/myenv")).name in ("bin", "Scripts")
    True
    """

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
    """Get the path to the Python interpreter inside a virtual environment.

    Detects platform, retrieves the absolute path to the appropriate Python executable
    (python.exe on Windows; python on POSIX) within a supplied venv directory.

    Parameters
    ----------
    venv_path : Path
        Path to the root of the virtual environment.

    Returns
    -------
    Path
        Path to the Python interpreter within the given venv.

    Raises
    ------
    None

    See Also
    --------
    get_venv_pip_executable : Get the pip executable inside venv.
    get_venv_bin_dir : Get venv executable directory.

    Examples
    --------
    >>> from pathlib import Path
    >>> ve = get_venv_python_executable(Path("/tmp/testenv"))
    >>> assert ve.name.startswith("python")
    """
    bin_dir = get_venv_bin_dir(venv_path)
    platform = sys.platform
    if platform == "win32":
        return bin_dir / "python.exe"
    return bin_dir / "python"


def get_venv_pip_executable(venv_path: Path) -> Path:
    """Get the path to the pip executable inside a virtual environment.

    Determines the correct pip executable path for the detected platform within a supplied venv directory.

    Parameters
    ----------
    venv_path : Path
        Path to the root of the virtual environment.

    Returns
    -------
    Path
        Path to the pip executable within the given venv.

    Raises
    ------
    None

    Examples
    --------
    >>> from pathlib import Path
    >>> pip_path = get_venv_pip_executable(Path("/tmp/testenv"))
    >>> assert "pip" in pip_path.name
    """
    bin_dir = get_venv_bin_dir(venv_path)
    platform = sys.platform
    if platform == "win32":
        return bin_dir / "pip.exe"
    return bin_dir / "pip"


def get_python_executable() -> str:
    """Get the Python interpreter for the current process environment.

    Returns the full executable path for the active Python interpreter. Delegates to
    `src.setup.venv.get_python_executable` when available for improved testability.

    Returns
    -------
    str
        Full path to Python executable.

    Raises
    ------
    None

    Examples
    --------
    >>> exe = get_python_executable()
    >>> assert exe.endswith("python") or exe.endswith("python.exe")
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


def run_program(
    program_name: str, program_file: Path, stream_output: bool = False
) -> bool:
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
        proc = subprocess_mod.Popen(
            [python, "-m", program_file.with_suffix("").name], cwd=proj_root, env=env
        )
        return proc.wait() == 0
    result = subprocess_mod.run(
        [python, "-m", program_file.with_suffix("").name],
        cwd=proj_root,
        capture_output=True,
        text=True,
        env=env,
    )
    return getattr(result, "returncode", 0) == 0


def manage_virtual_environment() -> None:
    """Invoke the refactored virtual environment manager.

    This wrapper prepares a lightweight UI adapter and synchronises a
    few helper functions so the venv manager can be exercised in tests
    without the full interactive runtime.
    """
    vm: Optional[ModuleType] = None
    try:
        import src.setup.fs_utils as fs_utils
        import src.setup.venv_manager as vm

        if vm is not None:
            vm.create_safe_path = fs_utils.create_safe_path  # type: ignore[attr-defined]
            vm.safe_rmtree = fs_utils.safe_rmtree  # type: ignore[attr-defined]
    except Exception:
        # If direct import failed, attempt to pick up a test-installed
        # module from sys.modules (tests may insert a fake manager there).
        vm = sys.modules.get("src.setup.venv_manager")
        try:
            import src.setup.fs_utils as fs_utils

            if vm is not None:
                try:
                    vm.create_safe_path = fs_utils.create_safe_path  # type: ignore[attr-defined]
                    vm.safe_rmtree = fs_utils.safe_rmtree  # type: ignore[attr-defined]
                except Exception:
                    pass
        except Exception:
            pass

    class _UI:
        import logging

        logger = logging.getLogger("src.setup.app")

        # Delegate to the concrete helper implementations via lazy import.
        def _ask_text(self, *a: Any, **k: Any) -> str:
            """Ask the user for free-text input using the concrete prompt helper.

            This performs a lazy import of ``src.setup.app_prompts.ask_text`` so
            that there is no hard dependency on any legacy shim module. If the
            concrete helper is not available the function returns an empty
            string to preserve the previous non-fatal behaviour.

            Parameters
            ----------
            *a
                Positional arguments forwarded to the prompt helper.
            **k
                Keyword arguments forwarded to the prompt helper.

            Returns
            -------
            str
                Prompt result, or empty string when a helper is unavailable.
            """
            try:
                from src.setup.app_prompts import ask_text as _ask

                return _ask(*a, **k)
            except (ImportError, AttributeError):
                return ""

        def _ui_has_rich(self) -> bool:
            """Return whether a rich console is available via the concrete UI helper.

            Returns
            -------
            bool
                True when the UI helper reports rich console support; defaults
                to True if the concrete helper cannot be imported.
            """
            try:
                from src.setup.app_ui import ui_has_rich as _uh

                return bool(_uh())
            except (ImportError, AttributeError):
                return True

        def _rprint(self, *a: Any, **k: Any) -> None:
            """Print via the concrete UI print helper or fallback to builtin print.

            This attempts a lazy import of ``src.setup.app_ui.rprint`` and calls
            it. If unavailable the function falls back to the standard
            ``print`` implementation.

            Parameters
            ----------
            *a
                Positional arguments forwarded to the printer.
            **k
                Keyword arguments forwarded to the printer.

            Returns
            -------
            None
                The builtin print returns None.
            """
            try:
                from src.setup.app_ui import rprint as _rp

                return _rp(*a, **k)
            except (ImportError, AttributeError):
                print(*a, **k)
                return None

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
        _venvmod: Optional[ModuleType] = None
        _venv_orig: dict[str, tuple[bool, Any | None]] = {}
        try:
            import src.setup.venv as _venvmod

            for _name in (
                "is_venv_active",
                "get_venv_python_executable",
                "get_venv_pip_executable",
                "get_python_executable",
            ):
                # Prefer explicit, local implementations and concrete
                # helpers rather than reading a legacy shim from
                # ``sys.modules``. This removes implicit global state and
                # makes the behaviour easier to reason about for tests and
                # for future refactors.
                candidate = globals().get(_name)
                if candidate is None:
                    try:
                        # Attempt to pick up the concrete helper from the
                        # refactored venv module if available.
                        import src.setup.app_venv as concrete_venv

                        candidate = getattr(concrete_venv, _name, None)
                    except Exception:
                        candidate = None
                if (
                    candidate is not None
                    and getattr(candidate, "__module__", None) != __name__
                ):
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
            _venv_orig = {}
        finally:
            # Always execute the loop to avoid unreachable code; condition inside.
            for _name, (had, orig) in _venv_orig.items():
                if _venvmod is not None:
                    if had:
                        setattr(_venvmod, _name, orig)
                    else:
                        if hasattr(_venvmod, _name):
                            try:
                                delattr(_venvmod, _name)
                            except Exception:
                                pass

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
            pass  # No additional cleanup needed after loop restructuring


__all__ = [
    "get_venv_bin_dir",
    "get_venv_python_executable",
    "get_venv_pip_executable",
    "get_python_executable",
    "is_venv_active",
    "run_program",
    "manage_virtual_environment",
]
