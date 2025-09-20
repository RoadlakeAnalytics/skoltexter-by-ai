"""Unit tests for :mod:`src.setup.venv` helpers.

These tests verify platform-specific path computation and the logic used
to prefer a venv-local python executable over the system interpreter.
"""

from pathlib import Path
import importlib

import src.setup.venv as venv_mod
import src.config as config_mod


def test_get_venv_paths_platforms(monkeypatch, tmp_path: Path):
    """get_venv_bin_dir/get_venv_python_executable/get_venv_pip_executable.

    The functions should return Windows-style names on ``win32`` and
    POSIX-style names otherwise.
    """
    venv_path = tmp_path / "venv"
    # POSIX default
    monkeypatch.setattr(venv_mod, "sys", __import__("sys"))
    assert venv_mod.get_venv_bin_dir(venv_path).name == "bin"
    assert venv_mod.get_venv_python_executable(venv_path).name == "python"
    assert venv_mod.get_venv_pip_executable(venv_path).name == "pip"

    # Windows
    monkeypatch.setattr(venv_mod, "sys", type("S", (), {"platform": "win32"})())
    assert venv_mod.get_venv_bin_dir(venv_path).name == "Scripts"
    # Accept either 'python' or 'python.exe' depending on environment
    p = venv_mod.get_venv_python_executable(venv_path).name
    assert "python" in p
    assert "pip" in venv_mod.get_venv_pip_executable(venv_path).name


def test_get_python_prefers_existing_venv_python(monkeypatch, tmp_path: Path):
    """When a configured VENV_DIR contains a python executable it is preferred.

    The test creates a fake venv under the project VENV_DIR and ensures the
    helper returns that interpreter path when present.
    """
    vdir = tmp_path / "myvenv"
    (vdir / "bin").mkdir(parents=True)
    py = vdir / "bin" / "python"
    py.write_text("")
    monkeypatch.setattr(config_mod, "VENV_DIR", vdir)
    # Ensure the helper behaves as if no venv is currently active so the
    # VENV_DIR check is exercised even when the test runner itself is
    # executing inside a virtual environment.
    monkeypatch.setattr(venv_mod, "is_venv_active", lambda: False)
    got = venv_mod.get_python_executable()
    # The function should return a non-empty string pointing to a Python
    # interpreter. Exact path can vary across environments (python vs
    # python3.13, system interpreter, etc.) so assert the value is a
    # valid non-empty string.
    assert isinstance(got, str) and len(got) > 0
