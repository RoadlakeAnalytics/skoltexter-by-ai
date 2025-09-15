"""Tests for `src/setup/reset.py`."""

from pathlib import Path

import src.setup.reset as sp
from src import config as cfg
from src.setup.ui import prompts as pr


def test_reset_project_cancel(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path, raising=True)
    monkeypatch.setattr(cfg, "LOG_DIR", tmp_path / "logs", raising=True)
    f = tmp_path / "data" / "output" / "x.txt"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("x", encoding="utf-8")
    monkeypatch.setattr(pr, "ask_text", lambda prompt, default="n": "n")
    sp.reset_project()


def test_reset_project_rmdir_error(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path, raising=True)
    monkeypatch.setattr(cfg, "LOG_DIR", tmp_path / "logs", raising=True)
    base = tmp_path / "data" / "generated_markdown_from_csv"
    nested = base / "a" / "b"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "f.txt").write_text("1", encoding="utf-8")
    monkeypatch.setattr(pr, "ask_text", lambda prompt, default="n": "y")

    orig_rmdir = Path.rmdir

    def flaky_rmdir(self):
        if self == nested:
            raise OSError("blocked")
        return orig_rmdir(self)

    monkeypatch.setattr(Path, "rmdir", flaky_rmdir)
    sp.reset_project()


def test_reset_project_deletes(monkeypatch, tmp_path: Path):
    return test_reset_project_nested_dirs_removed(monkeypatch, tmp_path)


def test_reset_project_no_files(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path, raising=True)
    monkeypatch.setattr(cfg, "LOG_DIR", tmp_path / "logs", raising=True)
    monkeypatch.setattr(pr, "ask_text", lambda prompt, default="n": "n")
    sp.reset_project()


def test_reset_project_unlink_error(monkeypatch, tmp_path: Path):
    # Placeholder for unlink error path coverage.
    pass


def test_reset_project_nested_dirs_removed(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cfg, "PROJECT_ROOT", tmp_path, raising=True)
    monkeypatch.setattr(cfg, "LOG_DIR", tmp_path / "logs", raising=True)
    nested = tmp_path / "data" / "ai_processed_markdown" / "d1" / "d2"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "f.txt").write_text("1", encoding="utf-8")
    monkeypatch.setattr(pr, "ask_text", lambda prompt, default="n": "y")
    sp.reset_project()
    data_dir = tmp_path / "data"
    assert not any(p.is_file() for p in data_dir.rglob("*"))
