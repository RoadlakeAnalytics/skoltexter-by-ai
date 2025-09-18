"""File handling utilities for AI processing.

This module knows how to find markdown files and save processed outputs.
It performs only file I/O and does not contact external services.
"""

import json
from pathlib import Path
from typing import Any

from src.config import (
    AI_PROCESSED_FILENAME_SUFFIX,
    AI_PROCESSED_MARKDOWN_SUBDIR,
    AI_RAW_RESPONSE_FILENAME_SUFFIX,
    AI_RAW_RESPONSES_SUBDIR,
)


def find_markdown_files(input_dir: Path) -> list[Path]:
    """Find markdown files in the given directory.

    Parameters
    ----------
    input_dir : Path
        Directory to search for ``*.md`` files.

    Returns
    -------
    list[Path]
        Sorted list of markdown file paths found in `input_dir`.
    """
    return sorted(list(Path(input_dir).glob("*.md")))


def save_processed_files(
    school_id: str, markdown: str, raw_json: dict[str, Any], output_dir_base: Path
) -> None:
    """Save AI processed markdown and raw JSON response for a school.

    Parameters
    ----------
    school_id : str
        Identifier for the school (used as filename prefix).
    markdown : str
        The AI-generated markdown content to write.
    raw_json : dict[str, Any]
        Raw JSON response from the AI service to persist.
    output_dir_base : Path
        Base directory under which markdown and JSON subdirectories are created.

    Returns
    -------
    None
    """
    md_dir = output_dir_base / AI_PROCESSED_MARKDOWN_SUBDIR
    json_dir = output_dir_base / AI_RAW_RESPONSES_SUBDIR
    md_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)
    md_path = md_dir / f"{school_id}{AI_PROCESSED_FILENAME_SUFFIX}"
    json_path = json_dir / f"{school_id}{AI_RAW_RESPONSE_FILENAME_SUFFIX}"
    md_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(
        json.dumps(raw_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )
