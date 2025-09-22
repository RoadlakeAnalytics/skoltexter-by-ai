"""Markdown Generator Runner Module.

This module provides the testable, programmatic entrypoints and logging configuration utilities
for the markdown generator step in the school data pipeline. It acts as the boundary API
between orchestration/UI layers and the core markdown generation logic, enforcing strict separation
of concerns as described in AGENTS.md standards.

Its primary responsibility is to expose directly callable functions that replace legacy script-based
interfaces, supporting robust automation, integration testing, and reproducibility. No business logic
is present; all pipeline functionality is delegated to `processor.py` and `templating.py`. This ensures
the core pipeline can run independently of any UI or CLI, fully in line with the project's decoupling targets.

References
----------
- See AGENTS.md Section 3 (Architecture).
- See data/templates/school_description_template.md and src/pipeline/markdown_generator/processor.py for implementation details.
- Tests: tests/pipeline/markdown_generator/test_runner_unit.py.

Notes
-----
All configuration values (paths, filenames, log format, etc.) are loaded via src/config.py as portfolio best practice.
Docstrings and API interfaces comply strictly with NumPy and AGENTS.md requirements.

Examples
--------
Basic usage from Python code:

>>> from src.pipeline.markdown_generator.runner import run_from_config, configure_logging
>>> configure_logging(log_level="INFO")  # optional: set up logging
>>> success = run_from_config()  # run with config defaults
>>> assert isinstance(success, bool)
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.config import (
    LOG_DIR,
    LOG_FILENAME_GENERATE_MARKDOWNS,
    LOG_FORMAT,
    ORIGINAL_CSV_PATH,
    OUTPUT_MARKDOWN_DIR,
    TEMPLATE_FILE_PATH,
)

from .processor import build_template_context, process_csv_and_generate_markdowns
from .templating import load_template_and_placeholders, render_template

logger = logging.getLogger(__name__)


def configure_logging(log_level: str = "INFO", enable_file: bool = True) -> None:
    r"""Configure logging for markdown generator pipeline execution.

    Sets up both stream (console) and optional file logging handlers, applying the log format from project
    configuration. File handler creation errors are intentionally swallowed to ensure test isolation
    and reproducibility. This mirrors legacy script entrypoint behavior but is resilient for modern pipeline usage.

    Parameters
    ----------
    log_level : str, optional
        The logging level (e.g., "INFO", "DEBUG"). Defaults to "INFO".
    enable_file : bool, optional
        Whether to enable writing logs to a file. If True, uses LOG_DIR and LOG_FILENAME_GENERATE_MARKDOWNS
        from src.config.py. Defaults to True.

    Returns
    -------
    None
        No return value.

    Raises
    ------
    None
        All exceptions during file handler creation are swallowed for safety.

    See Also
    --------
    src.config.py : Contains LOG_DIR, LOG_FILENAME_GENERATE_MARKDOWNS, and LOG_FORMAT.
    run_from_config : Pipeline runner below.

    Notes
    -----
    This function clears out all existing handlers for root logger before configuring new ones.
    It is safe to call repeatedly; it is idempotent.

    Examples
    --------
    >>> from src.pipeline.markdown_generator.runner import configure_logging
    >>> configure_logging(log_level="DEBUG", enable_file=False)
    """
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if enable_file:
        try:
            LOG_DIR.mkdir(exist_ok=True)
            handlers.insert(
                0,
                logging.FileHandler(
                    LOG_DIR / LOG_FILENAME_GENERATE_MARKDOWNS, mode="a"
                ),
            )
        except Exception:
            pass
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format=LOG_FORMAT,
        handlers=handlers,
    )


def run_from_config(
    csv_path: Path | None = None,
    template_path: Path | None = None,
    output_dir: Path | None = None,
) -> bool:
    """Run markdown generation using provided paths or defaults from config.

    Returns
    -------
    bool
        True on success (files generated or skipped), False on I/O failure.
    """
    csv_path = Path(csv_path) if csv_path is not None else ORIGINAL_CSV_PATH
    template_path = (
        Path(template_path) if template_path is not None else Path(TEMPLATE_FILE_PATH)
    )
    output_dir = Path(output_dir) if output_dir is not None else OUTPUT_MARKDOWN_DIR
    try:
        tpl_content, placeholders = load_template_and_placeholders(template_path)
        count = process_csv_and_generate_markdowns(
            csv_path, tpl_content, placeholders, output_dir
        )
        logger.info("Generated %d markdown files", count)
        return True
    except Exception as exc:
        logger.exception("Failed to generate markdowns: %s", exc)
        return False


__all__ = [
    "build_template_context",
    "configure_logging",
    "load_template_and_placeholders",
    "render_template",
    "run_from_config",
]
