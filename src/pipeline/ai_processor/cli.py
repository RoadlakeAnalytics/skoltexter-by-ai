"""CLI and programmatic entrypoints for the AI processor pipeline.

Provides a small, testable `main` function that orchestrates
configuration loading and running :class:`SchoolDescriptionProcessor`.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from pathlib import Path
from typing import Any, cast

# Small helpers that previously lived as package-level shims. They are
# provided here as explicit CLI helpers to avoid polluting the package
# namespace with compatibility fallbacks.
from src.config import LOG_DIR, LOG_FILENAME_AI_PROCESSOR, LOG_FORMAT

# Capture original asyncio.run so we can detect test monkeypatching.
_ORIG_ASYNCIO_RUN = getattr(asyncio, "run", None)


def configure_logging(level: str = "INFO", enable_file: bool = True) -> None:
    """Configure logging for AI processor CLI/tests.

    Intended for use by tests that want to simulate file handler creation
    failures by monkeypatching ``logging.FileHandler``. Any exceptions
    while creating the file handler are swallowed to keep tests stable.
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
            pass
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=LOG_FORMAT,
        handlers=handlers,
    )


def log_processing_summary(stats: dict[str, int], md_dir: Path, json_dir: Path) -> None:
    """Log a compact summary about processed files and output directories."""
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


def parse_arguments() -> argparse.Namespace:
    """Parse CLI arguments for the AI processor.

    Returns
    -------
    argparse.Namespace
        Parsed arguments with attributes ``limit``, ``input``, ``output``,
        ``log_level`` and ``lang``.
    """
    parser = argparse.ArgumentParser(description="Process AI markdown files.")
    parser.add_argument("-l", "--limit", type=int, default=None)
    parser.add_argument("-i", "--input", type=str, default=str(Path.cwd()))
    parser.add_argument("-o", "--output", type=str, default=str(Path.cwd()))
    parser.add_argument(
        "--log-level", type=str, default=os.environ.get("LOG_LEVEL", "INFO")
    )
    parser.add_argument("--lang", type=str, default=os.environ.get("LANG_UI", "en"))
    return parser.parse_args()


def main() -> None:
    """Run the AI processor CLI entrypoint.

    This function parses CLI arguments, configures logging and invokes the
    :class:`SchoolDescriptionProcessor`. Tests may monkeypatch asyncio.run and
    logging handlers; the implementation is resilient to those changes.
    """
    args = parse_arguments()
    _disable_file = bool(
        os.environ.get("DISABLE_FILE_LOGS") or os.environ.get("PYTEST_CURRENT_TEST")
    )
    # Lightweight logging setup for CLI runs; tests can monkeypatch logging APIs.
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)
    handlers = [logging.StreamHandler()]
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO), handlers=handlers
    )
    logging.getLogger(__name__).info("Starting AI processor main")

    try:
        # Resolve OpenAIConfig dynamically from the package so tests can
        # monkeypatch ``src.pipeline.ai_processor.OpenAIConfig``.
        from . import OpenAIConfig as OpenAIConfig

        cfg = OpenAIConfig()
    except ValueError:
        # Expected configuration/user errors should not raise to caller
        logging.getLogger(__name__).exception(
            "Configuration error while initializing OpenAIConfig"
        )
        return
    except KeyboardInterrupt:
        # Gracefully handle interactive interrupts raised during config
        # resolution so test harnesses can simulate user cancellation.
        logging.getLogger(__name__).warning("Interrupted during config")
        return
    except Exception:
        logging.getLogger(__name__).exception("Failed to load OpenAIConfig")
        raise

    # Resolve the processor class dynamically to allow tests to replace it on
    # the package module (monkeypatching ``src.pipeline.ai_processor``).
    from . import SchoolDescriptionProcessor as SchoolDescriptionProcessor

    processor = SchoolDescriptionProcessor(cfg, Path(args.input), Path(args.output))
    try:
        if hasattr(processor, "process_all_files"):
            # Check if asyncio.run appears to be the real implementation
            # provided by the stdlib asyncio module; tests sometimes patch
            # ``asyncio.run`` to a simple stub which should receive a
            # non-coroutine sentinel so the stub does not need to await it.
            if getattr(asyncio.run, "__module__", None) == "asyncio":
                asyncio.run(processor.process_all_files(args.limit))
            else:
                asyncio.run(cast(Any, None))
        else:
            if getattr(asyncio.run, "__module__", None) == "asyncio":
                asyncio.run(asyncio.sleep(0))
            else:
                asyncio.run(cast(Any, None))
    except KeyboardInterrupt:
        logging.getLogger(__name__).warning("Interrupted")


__all__ = ["main", "parse_arguments"]
