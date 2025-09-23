"""Virtual environment path helpers.

Helpers for resolving platform-specific paths inside a Python virtual
environment. These functions are side-effect free and return Path objects.
"""

from __future__ import annotations

import sys
from pathlib import Path


def get_venv_bin_dir(venv_path: Path) -> Path:
    """Return the platform-specific binary directory inside a virtualenv.

    Parameters
    ----------
    venv_path : Path
        Path to the root of the virtual environment directory.

    Returns
    -------
    Path
        Path to the binaries directory ("Scripts" on Windows, "bin" otherwise).

    Examples
    --------
    >>> from pathlib import Path
    >>> get_venv_bin_dir(Path('/tmp/venv')).as_posix()
    '/tmp/venv/bin'
    """
    return venv_path / ("Scripts" if sys.platform == "win32" else "bin")


def get_venv_python_executable(venv_path: Path) -> Path:
    """Return the python executable path for the given virtualenv.

    Parameters
    ----------
    venv_path : Path
        Path to the virtual environment directory.

    Returns
    -------
    Path
        Path to the Python interpreter inside the virtualenv.
    """
    bin_dir = get_venv_bin_dir(venv_path)
    return bin_dir / ("python.exe" if sys.platform == "win32" else "python")


def get_venv_pip_executable(venv_path: Path) -> Path:
    """Return the pip executable path for the given virtualenv.

    Parameters
    ----------
    venv_path : Path
        Path to the virtual environment directory.

    Returns
    -------
    Path
        Path to the pip executable inside the virtualenv.
    """
    bin_dir = get_venv_bin_dir(venv_path)
    return bin_dir / ("pip.exe" if sys.platform == "win32" else "pip")


def is_venv_active() -> bool:
    """Return True if the current Python process is running inside a venv."""
    return bool(sys.prefix) and (Path(sys.prefix) != Path(sys.base_prefix))


def get_python_executable() -> str:
    """Return the best Python executable for running subprocesses.

    If running inside an active venv, return the current interpreter. Otherwise
    prefer the interpreter inside the configured venv directory if present.
    """
    if is_venv_active():
        return sys.executable
    from src.config import VENV_DIR

    vpy = get_venv_python_executable(VENV_DIR)
    if vpy.exists():
        return str(vpy)
    return sys.executable

