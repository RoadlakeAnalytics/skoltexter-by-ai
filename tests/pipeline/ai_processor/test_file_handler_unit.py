"""Unit tests for AI processor file handling utilities. (unique name)
"""

import json
from pathlib import Path

from src.pipeline.ai_processor import file_handler as fh
from src.config import (
    AI_PROCESSED_MARKDOWN_SUBDIR,
    AI_RAW_RESPONSES_SUBDIR,
    AI_PROCESSED_FILENAME_SUFFIX,
    AI_RAW_RESPONSE_FILENAME_SUFFIX,
)


def test_find_markdown_files(tmp_path: Path) -> None:
    (tmp_path / "b.md").write_text("b")
    (tmp_path / "a.md").write_text("a")
    (tmp_path / "c.md").write_text("c")
    (tmp_path / "ignore.txt").write_text("x")

    found = fh.find_markdown_files(tmp_path)
    assert [p.name for p in found] == ["a.md", "b.md", "c.md"]


def test_save_processed_files(tmp_path: Path) -> None:
    school_id = "S1"
    markdown = "## Hello"
    raw = {"foo": "bar"}

    fh.save_processed_files(school_id, markdown, raw, tmp_path)

    md_dir = tmp_path / AI_PROCESSED_MARKDOWN_SUBDIR
    json_dir = tmp_path / AI_RAW_RESPONSES_SUBDIR

    md_path = md_dir / f"{school_id}{AI_PROCESSED_FILENAME_SUFFIX}"
    json_path = json_dir / f"{school_id}{AI_RAW_RESPONSE_FILENAME_SUFFIX}"

    assert md_path.exists()
    assert md_path.read_text(encoding="utf-8") == markdown

    parsed = json.loads(json_path.read_text(encoding="utf-8"))
    assert parsed == raw
