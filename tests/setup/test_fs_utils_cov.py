"""Tests for filesystem safety helpers (create_safe_path / safe_rmtree)."""

from pathlib import Path
import shutil

import src.setup.fs_utils as fs_utils
import src.config as cfg


def test_create_safe_path_denies_project_root(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cfg, 'PROJECT_ROOT', tmp_path)
    try:
        fs_utils.create_safe_path(tmp_path)
        raise AssertionError('Expected PermissionError')
    except PermissionError:
        pass


def test_create_safe_path_and_safe_rmtree(tmp_path: Path, monkeypatch):
    # Configure a whitelisted output directory under the project root
    project = tmp_path / 'proj'
    project.mkdir()
    out = project / 'output'
    out.mkdir()
    monkeypatch.setattr(cfg, 'PROJECT_ROOT', project)
    monkeypatch.setattr(cfg, 'LOG_DIR', project / 'logs')
    monkeypatch.setattr(cfg, 'VENV_DIR', project / 'venv')

    # Path under whitelist should be allowed
    validated = fs_utils.create_safe_path(out)
    assert isinstance(validated, Path)

    # Create folder and remove it using safe_rmtree
    (out / 'a').write_text('x')
    assert out.exists()
    fs_utils.safe_rmtree(validated)
    assert not out.exists()


def test_create_safe_path_allows_pycache(tmp_path: Path, monkeypatch):
    project = tmp_path / 'proj'
    d = project / 'some' / '__pycache__'
    d.mkdir(parents=True)
    monkeypatch.setattr(cfg, 'PROJECT_ROOT', project)
    res = fs_utils.create_safe_path(d)
    assert res.name == '__pycache__'

