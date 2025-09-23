"""Generate final HTML website from CSV and AI-generated Markdown.

This module provides a headless runner that merges CSV data and
AI-generated Markdown content and renders the final HTML site using
project templates. It is intended for programmatic invocation.

Usage Examples
--------------
Typical programmatic usage with config defaults::

    from src.pipeline.website_generator.runner import run_from_config
    result = run_from_config()
    assert result is True

Explicit path usage::

    from pathlib import Path
    from src.pipeline.website_generator.runner import run_from_config

    run_from_config(
        csv_path=Path("data/my_schools.csv"),
        ai_markdown_dir=Path("outputs/ai_md"),
        output_file=Path("sites/final.html")
    )

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
    """Generate the final HTML website from CSV and AI Markdown sources.

    If any argument is ``None``, project-level defaults from
    ``src.config`` are used. The function returns ``True`` on success and
    ``False`` if an error occurred; exceptions are logged.

    Parameters
    ----------
    csv_path : pathlib.Path or None, optional
        Source CSV file containing tabular school data. If ``None``, uses
        ``ORIGINAL_CSV_PATH`` from configuration.
    ai_markdown_dir : pathlib.Path or None, optional
        Directory containing AI-generated Markdown files. If ``None``, uses
        ``AI_MARKDOWN_DIR`` from configuration.
    output_file : pathlib.Path or None, optional
        Destination path for the generated HTML site. If ``None``, uses
        ``OUTPUT_HTML_FILE`` from configuration.

    Returns
    -------
    bool
        ``True`` if generation succeeded and the output was written to disk;
        ``False`` if an error occurred (all errors are logged).

    Examples
    --------
    Basic usage with config defaults:

    >>> from src.pipeline.website_generator.runner import run_from_config
    >>> result = run_from_config()
    >>> assert result in (True, False)

    Custom paths for manual runs:

    >>> from pathlib import Path
    >>> from src.pipeline.website_generator.runner import run_from_config
    >>> run_from_config(
    ...     csv_path=Path("data/my_schools.csv"),
    ...     ai_markdown_dir=Path("outputs/ai_md"),
    ...     output_file=Path("sites/final.html")
    ... )
    True

    Handling missing/empty input with fallback HTML (no raise):

    >>> from pathlib import Path
    >>> from src.pipeline.website_generator.runner import run_from_config
    >>> # Assume "tests/data/empty.csv" is empty
    >>> result = run_from_config(csv_path=Path("tests/data/empty.csv"))
    >>> assert result is True

    Simulating a disk permission failure (returns False):

    >>> from pathlib import Path
    >>> from src.pipeline.website_generator.runner import run_from_config
    >>> result = run_from_config(output_file=Path("/protected/final.html"))
    >>> assert result is False

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
