"""Additional tests for AI file handling that exercise edge-cases."""

from pathlib import Path
import json

from src.pipeline.ai_processor import file_handler as fh


def test_find_markdown_files_empty(tmp_path: Path) -> None:
    """An empty directory yields an empty list of markdown files."""
    found = fh.find_markdown_files(tmp_path)
    assert found == []


def test_save_processed_files_swallow_exceptions(monkeypatch, tmp_path: Path) -> None:
    """If writing fails the function should not raise an exception."""
    # Make Path.write_text raise on first call to simulate IO errors
    orig_write = Path.write_text

    def bad_write(self, *a, **k):
        raise OSError("boom")

    monkeypatch.setattr(Path, "write_text", bad_write)
    try:
        fh.save_processed_files("S1", "md", {"a": 1}, tmp_path)
    finally:
        monkeypatch.setattr(Path, "write_text", orig_write)

