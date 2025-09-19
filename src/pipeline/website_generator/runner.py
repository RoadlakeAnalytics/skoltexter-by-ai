"""Runner helpers for website generation pipeline.

Provides a simple programmatic entry that composes CSV data with AI
markdown outputs and writes the final HTML file.
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.config import (
    AI_MARKDOWN_DIR,
    ORIGINAL_CSV_PATH,
    OUTPUT_HTML_FILE,
    WEBSITE_TEMPLATE_PATH,
)

from .data_aggregator import (
    load_school_data,
)
from .renderer import generate_final_html, write_html_output

logger = logging.getLogger(__name__)


def run_from_config(
    csv_path: Path | None = None,
    ai_markdown_dir: Path | None = None,
    output_file: Path | None = None,
) -> bool:
    """Run website generation using provided or configured paths.

    Parameters
    ----------
    csv_path : Path | None
        Optional path to the source CSV file. If ``None`` the configured
        default ``ORIGINAL_CSV_PATH`` is used.
    ai_markdown_dir : Path | None
        Optional directory containing AI-generated markdown files.
    output_file : Path | None
        Optional destination HTML file path.

    Returns
    -------
    bool
        True on successful generation, False on any error.
    """
    csv_path = Path(csv_path) if csv_path is not None else ORIGINAL_CSV_PATH
    ai_markdown_dir = (
        Path(ai_markdown_dir) if ai_markdown_dir is not None else AI_MARKDOWN_DIR
    )
    output_file = Path(output_file) if output_file is not None else OUTPUT_HTML_FILE
    try:
        schools = load_school_data(csv_path, ai_markdown_dir)
        if not schools:
            write_html_output("<html><body><h1>No data</h1></body></html>", output_file)
            return True
        html = generate_final_html(schools, WEBSITE_TEMPLATE_PATH)
        write_html_output(html, output_file)
        return True
    except Exception:
        logger.exception("Failed to generate website")
        return False


__all__ = ["run_from_config"]
