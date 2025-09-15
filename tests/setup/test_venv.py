"""Tests for `src/setup/venv.py`."""

import sys
from pathlib import Path

from src import config as cfg
from src.setup import venv as sp


def test_get_venv_exec_on_windows(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sp.sys, "platform", "win32")
    v = tmp_path / "venv"
    assert sp.get_venv_bin_dir(v).name == "Scripts"
    assert sp.get_venv_python_executable(v).name == "python.exe"
    assert sp.get_venv_pip_executable(v).name == "pip.exe"


def test_get_python_executable_variants(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sp, "is_venv_active", lambda: True)
    assert sp.get_python_executable() == sys.executable
    monkeypatch.setattr(sp, "is_venv_active", lambda: False)
    fake_py = (
        tmp_path
        / "venv"
        / ("bin" if sys.platform != "win32" else "Scripts")
        / ("python.exe" if sys.platform == "win32" else "python")
    )
    fake_py.parent.mkdir(parents=True, exist_ok=True)
    fake_py.write_text("", encoding="utf-8")
    monkeypatch.setattr(cfg, "VENV_DIR", tmp_path / "venv", raising=True)
    assert Path(sp.get_python_executable()).exists()
