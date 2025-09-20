"""Unit tests for filesystem helpers in ``src.setup.fs_utils``."""

from pathlib import Path

import src.setup.fs_utils as fs_utils
import src.config as cfg


def test_create_safe_path_denies_project_root(monkeypatch):
    # Point project root to a tmp path
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp, raising=False)
    try:
        fs_utils.create_safe_path(tmp)
        raise AssertionError("Expected PermissionError")
    except PermissionError:
        pass


def test_create_safe_path_and_safe_rmtree(monkeypatch, tmp_path: Path):
    # Allow removal under the 'output' whitelist
    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path, raising=False)
    out_root = tmp_path / "output"
    target = out_root / "to_delete"
    target.mkdir(parents=True, exist_ok=True)
    vp = fs_utils.create_safe_path(target)
    assert isinstance(vp, Path)
    # safe_rmtree should remove the directory
    fs_utils.safe_rmtree(vp)
    assert not target.exists()
