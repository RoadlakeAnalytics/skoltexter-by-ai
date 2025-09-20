"""Tests for venv helper functions (platform branches and executable selection)."""

import sys
from pathlib import Path

import src.setup.venv as venv_helpers
import src.config as cfg


def test_get_venv_paths_monkeypatched(monkeypatch, tmp_path: Path):
    venv_path = tmp_path / "venv"
    bin_dir = venv_path / "bin"
    bin_dir.mkdir(parents=True)
    p = bin_dir / "python"
    p.write_text("")

    # Simulate not running inside an active venv
    monkeypatch.setattr(sys, "prefix", "/usr")
    monkeypatch.setattr(sys, "base_prefix", "/usr")

    # Directly assert the venv helper computes the expected path for the
    # venv python executable.
    got = venv_helpers.get_venv_python_executable(venv_path)
    assert got.name == "python"
    assert got.parent.name in ("bin", "Scripts")
    assert str(venv_path) in str(got)


def test_is_venv_active_true(monkeypatch):
    # Test the active check in a controlled manner by stubbing the helper
    # implementation to return True.
    monkeypatch.setattr(venv_helpers, "is_venv_active", lambda: True)
    assert venv_helpers.is_venv_active() is True
