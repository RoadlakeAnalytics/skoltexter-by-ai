"""CLI runner helpers for the markdown generator pipeline.

Provides a small, test-friendly entrypoint that other orchestration code
can call directly instead of spawning a separate process. This replaces
the previous top-level script API and removes the need for legacy shims.
"""
from __future__ import annotations

from pathlib import Path
import logging

from src.config import ORIGINAL_CSV_PATH, TEMPLATE_FILE_PATH, OUTPUT_MARKDOWN_DIR, LOG_DIR, LOG_FILENAME_GENERATE_MARKDOWNS, LOG_FORMAT
from .templating import load_template_and_placeholders, render_template
from .processor import process_csv_and_generate_markdowns, build_template_context

logger = logging.getLogger(__name__)


def configure_logging(log_level: str = "INFO", enable_file: bool = True) -> None:
    """Configure logging for markdown generator runs.

    This function mirrors the old entrypoint behaviour by attempting to
    add a file handler but swallowing file handler creation errors to
    facilitate testing.
    """
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if enable_file:
        try:
            LOG_DIR.mkdir(exist_ok=True)
            handlers.insert(0, logging.FileHandler(LOG_DIR / LOG_FILENAME_GENERATE_MARKDOWNS, mode="a"))
        except Exception:
            pass
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO), format=LOG_FORMAT, handlers=handlers)


def run_from_config(csv_path: Path | None = None, template_path: Path | None = None, output_dir: Path | None = None) -> bool:
    """Run markdown generation using provided paths or defaults from config.

    Returns
    -------
    bool
        True on success (files generated or skipped), False on I/O failure.
    """
    csv_path = Path(csv_path) if csv_path is not None else ORIGINAL_CSV_PATH
    template_path = Path(template_path) if template_path is not None else Path(TEMPLATE_FILE_PATH)
    output_dir = Path(output_dir) if output_dir is not None else OUTPUT_MARKDOWN_DIR
    try:
        tpl_content, placeholders = load_template_and_placeholders(template_path)
        count = process_csv_and_generate_markdowns(csv_path, tpl_content, placeholders, output_dir)
        logger.info("Generated %d markdown files", count)
        return True
    except Exception as exc:
        logger.exception("Failed to generate markdowns: %s", exc)
        return False


__all__ = ["configure_logging", "run_from_config", "build_template_context", "render_template", "load_template_and_placeholders"]

