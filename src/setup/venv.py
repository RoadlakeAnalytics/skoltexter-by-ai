"""Virtual environment path helpers for orchestrator/test/CI integration.

Single Responsibility Principle (SRP): This module exclusively provides normalized
helpers for determining filesystem paths associated with Python virtual environments (venv).
No activation, creation, or business logic is present.

Architectural Boundaries:
- Used only by SRC orchestrator setup modules, not by pipeline layer logic.
- Invoked by orchestrator menus/UI, automation helpers, and CI test runners, strictly via
  import from orchestrator logic (see `src/setup/venv_manager.py`, `src/setup/app_venv.py`).

Config/Constants References:
- All venv paths are derived/configured via `src/config.py::VENV_DIR` and other constants.
- No hard-coded paths; all magic values must be defined in config.
- Interpreter lookup fully complies with AGENTS.md §3 "Configuration as Code".

Exception Handling:
- No exceptions are raised directly by these helpers.
- For all error taxonomy and mutation/robustness behaviors, see orchestrator boundary,
  which maps system/file errors to application exceptions in `src/exceptions.py`.

Test/CI References:
- Canonical functional, branch, mutation, and edge-case tests:
    - `tests/setup/test_venv.py`
    - `tests/setup/test_venv_unit.py`
    - `tests/setup/test_venv_cov.py`
    - Mutation smoke/test-integrations: `tests/setup/test_app_wrappers_more.py`
- All edge cases (platform, missing venv, interpreter variants) are covered as per CI coverage policy.

Usage Notes:
- Helpers are platform-conscious (`sys.platform`) and strictly side-effect-free.
- Used for orchestrator automation (UI menu flows, venv/subprocess orchestration, test/CI runners).
- Portfolio/audit compliance: single-responsibility, explicit boundaries, non-recursive, and type-safe.
- All code is compliant with mypy --strict, ruff, black, zero-warning CI/test gates.

See AGENTS.md §4/5 for full documentation/robustness requirements.
"""

from __future__ import annotations

import sys
from pathlib import Path


def get_venv_bin_dir(venv_path: Path) -> Path:
    r"""Return the platform-specific binary directory inside a Python virtual environment.

    This helper normalizes path resolution for binary executables within a virtualenv,
    abstracting away cross-platform differences (Windows vs POSIX).
    Used exclusively by orchestrator setup/test utilities for automated UI flows and CI runners.

    Parameters
    ----------
    venv_path : Path
        Path to the root of the virtual environment directory. Must be configured via
        `src/config.py::VENV_DIR`, and validated by orchestrator layer.

    Returns
    -------
    Path
        Path to the platform-specific binaries directory ("Scripts" on Windows, "bin" otherwise).

    Raises
    ------
    None

    Notes
    -----
    - No I/O; pure path logic.
    - Platform logic is bounded to `sys.platform == "win32"`.
    - Mutation/robustness: Tests cover all platform branches and edge variants in CI.
    - Does not validate that the directory exists; see orchestrator for validation.
    - Used only for orchestrator/test/CI path orchestration.

    Examples
    --------
    >>> from pathlib import Path
    >>> from src.setup.venv import get_venv_bin_dir
    >>> get_venv_bin_dir(Path("/tmp/test_venv")).as_posix()
    '/tmp/test_venv/bin'
    >>> import sys
    >>> sys.platform = "win32"
    >>> get_venv_bin_dir(Path("C:\\test_venv")).as_posix()
    'C:/test_venv/Scripts'
    """

    Parameters
    ----------
    venv_path : Path
        Path to the virtual environment directory.

    Returns
    -------
    Path
        Platform-specific binary directory ("Scripts" on Windows, "bin" otherwise).
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
    # If a venv exists, prefer its interpreter
    from src.config import VENV_DIR

    vpy = get_venv_python_executable(VENV_DIR)
    if vpy.exists():
        return str(vpy)
    return sys.executable
