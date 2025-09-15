"""Virtual environment helpers used by setup utilities."""

from __future__ import annotations

import sys
from pathlib import Path


def get_venv_bin_dir(venv_path: Path) -> Path:
    return venv_path / ("Scripts" if sys.platform == "win32" else "bin")


def get_venv_python_executable(venv_path: Path) -> Path:
    bin_dir = get_venv_bin_dir(venv_path)
    return bin_dir / ("python.exe" if sys.platform == "win32" else "python")


def get_venv_pip_executable(venv_path: Path) -> Path:
    bin_dir = get_venv_bin_dir(venv_path)
    return bin_dir / ("pip.exe" if sys.platform == "win32" else "pip")


def is_venv_active() -> bool:
    return bool(sys.prefix) and (Path(sys.prefix) != Path(sys.base_prefix))


def get_python_executable() -> str:
    if is_venv_active():
        return sys.executable
    # If a venv exists, prefer its interpreter
    from src.config import VENV_DIR

    vpy = get_venv_python_executable(VENV_DIR)
    if vpy.exists():
        return str(vpy)
    return sys.executable
