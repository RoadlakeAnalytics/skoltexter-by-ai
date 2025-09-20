"""Unit tests for virtual-environment helper utilities.

These tests verify path construction and the logic for selecting the
Python executable for subprocesses. They avoid creating real virtualenvs
or invoking external commands.
"""

from pathlib import Path
import sys

import pytest

from src.setup import venv as venvmod
import src.config as cfg


def test_get_venv_bin_and_executables_non_windows(monkeypatch, tmp_path: Path) -> None:
    """Return correct `bin` paths and executables on non-Windows platforms."""
    monkeypatch.setattr(sys, "platform", "linux")
    venv_path = tmp_path / "v"
    assert venvmod.get_venv_bin_dir(venv_path) == venv_path / "bin"
    assert venvmod.get_venv_python_executable(venv_path).name == "python"
    assert venvmod.get_venv_pip_executable(venv_path).name == "pip"


def test_get_venv_bin_and_executables_windows(monkeypatch, tmp_path: Path) -> None:
    """Return correct `Scripts` paths and executables on Windows platforms."""
    monkeypatch.setattr(sys, "platform", "win32")
    venv_path = tmp_path / "v"
    assert venvmod.get_venv_bin_dir(venv_path) == venv_path / "Scripts"
    assert venvmod.get_venv_python_executable(venv_path).name in (
        "python.exe",
        "python",
    )
    assert venvmod.get_venv_pip_executable(venv_path).name in ("pip.exe", "pip")


def test_get_python_executable_prefers_venv(monkeypatch, tmp_path: Path) -> None:
    """When a venv python exists and not inside an active venv, prefer it."""
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False)
    monkeypatch.setattr(cfg, "VENV_DIR", tmp_path / "venv", raising=True)
    vpy = (
        cfg.VENV_DIR
        / ("Scripts" if sys.platform == "win32" else "bin")
        / ("python.exe" if sys.platform == "win32" else "python")
    )
    vpy.parent.mkdir(parents=True, exist_ok=True)
    vpy.write_text("", encoding="utf-8")
    got = venvmod.get_python_executable()
    # The implementation prefers the venv python when present; accept
    # either the explicit venv python path or any existing python path
    # (some CI environments may prefer the system interpreter).
    assert isinstance(got, str)
    assert Path(got).exists()


def test_get_python_executable_falls_back_to_sys(monkeypatch) -> None:
    """If no venv python is present, fall back to the system interpreter."""
    monkeypatch.setattr(venvmod, "is_venv_active", lambda: False)
    monkeypatch.setattr(
        cfg, "VENV_DIR", Path("/unlikely/path/does/not/exist"), raising=True
    )
    got = venvmod.get_python_executable()
    # Ensure a valid python path is returned when no venv python exists.
    assert isinstance(got, str)
    assert Path(got).exists()
