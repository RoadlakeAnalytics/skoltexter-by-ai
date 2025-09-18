"""AI processor package.

This package isolates API client logic, configuration loading and file
handling for AI processing.

It also exposes a small set of lightweight compatibility helpers that were
previously available on the legacy top-level entrypoint module
``src.program2_ai_processor``. Tests and other modules should prefer using
the concrete implementations in :mod:`src.pipeline.ai_processor`, however
the compatibility layer here reduces churn while the refactor is finished.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from types import SimpleNamespace

from src.config import LOG_DIR, LOG_FILENAME_AI_PROCESSOR, LOG_FORMAT

from .client import AIAPIClient
from .config import OpenAIConfig
from .file_handler import find_markdown_files, save_processed_files
from .processor import SchoolDescriptionProcessor
from . import cli as _cli

__all__ = [
    "OpenAIConfig",
    "AIAPIClient",
    "find_markdown_files",
    "save_processed_files",
    "SchoolDescriptionProcessor",
    # Compatibility helpers
    "configure_logging",
    "log_processing_summary",
    "tqdm_asyncio",
    # CLI entry
    "parse_arguments",
    "main",
]


def parse_arguments(*args, **kwargs):  # pragma: no cover - thin wrapper
    return _cli.parse_arguments(*args, **kwargs)


def main(*args, **kwargs):  # pragma: no cover - thin wrapper
    return _cli.main(*args, **kwargs)


class _TqdmAsyncioCompat:  # pragma: no cover - trivial compatibility shim
    """Compatibility shim exposing a ``gather`` attribute.

    Legacy tests sometimes monkeypatch ``<module>.tqdm_asyncio.gather``.  The
    processor implementation prefers to use an object with a ``gather``
    attribute; provide a tiny wrapper around ``asyncio.gather`` so tests can
    continue to patch it on the package module.
    """

    gather = staticmethod(asyncio.gather)


tqdm_asyncio = _TqdmAsyncioCompat()


def configure_logging(level: str = "INFO", enable_file: bool = True) -> None:
    """Configure logging for AI processor related CLI helpers.

    Parameters
    ----------
    level : str
        Logging level name (e.g. ``"INFO"`` or ``"DEBUG"``).
    enable_file : bool
        If ``True``, attempt to add a file handler writing to the
        AI processor log file. Errors while creating the file handler are
        swallowed to avoid breaking tests that monkeypatch logging APIs.
    """
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if enable_file:
        try:
            LOG_DIR.mkdir(exist_ok=True)
            handlers.insert(
                0, logging.FileHandler(LOG_DIR / LOG_FILENAME_AI_PROCESSOR, mode="a")
            )
        except Exception:
            # Intentionally swallow errors; tests may monkeypatch FileHandler
            # to raise and expect the configure call to handle that gracefully.
            pass
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=LOG_FORMAT,
        handlers=handlers,
    )


def log_processing_summary(stats: dict[str, int], md_dir: Path, json_dir: Path) -> None:
    """Log a compact summary about processed files and output directories.

    This helper mirrors behavior that previously lived on the legacy
    ``src.program2_ai_processor`` module so tests that import it can remain
    stable.
    """
    try:
        total = int(stats.get("total_files_in_input_dir", 0))
        skipped = int(stats.get("skipped_already_processed", 0))
        attempted = int(stats.get("attempted_to_process", 0))
        success = int(stats.get("successful_ai_processing", 0))
        failed = int(stats.get("failed_ai_processing", 0))

        logging.getLogger(__name__).info(
            "Processing summary: total=%d skipped=%d attempted=%d success=%d failed=%d",
            total,
            skipped,
            attempted,
            success,
            failed,
        )

        if md_dir.exists():
            try:
                md_files = [p for p in md_dir.iterdir() if p.is_file()]
                logging.getLogger(__name__).info(
                    "Markdown outputs: %d files in %s", len(md_files), md_dir
                )
            except Exception:
                logging.getLogger(__name__).exception(
                    "Failed to list markdown output dir %s", md_dir
                )

        if json_dir.exists():
            try:
                json_files = [p for p in json_dir.iterdir() if p.is_file()]
                logging.getLogger(__name__).info(
                    "Raw JSON responses: %d files in %s", len(json_files), json_dir
                )
            except Exception:
                logging.getLogger(__name__).exception(
                    "Failed to list json output dir %s", json_dir
                )
    except Exception:
        logging.getLogger(__name__).exception(
            "Error while summarizing processing stats"
        )
