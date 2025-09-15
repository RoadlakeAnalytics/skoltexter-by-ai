"""Thin orchestration CLI for AI processing.

This module is now a slim entrypoint that instantiates the pipeline
components located under `src.pipeline.ai_processor` and runs the
asynchronous processing flow.
"""

import argparse
import asyncio
import logging
import os
from pathlib import Path

from src.config import (
    DEFAULT_INPUT_MARKDOWN_DIR,
    DEFAULT_OUTPUT_BASE_DIR,
    LOG_DIR,
    LOG_FILENAME_AI_PROCESSOR,
    LOG_FORMAT,
    PROJECT_ROOT,
)
from src.pipeline.ai_processor import OpenAIConfig, SchoolDescriptionProcessor

logger = logging.getLogger(__name__)

# Compatibility alias used by legacy tests that patch `tqdm_asyncio.gather`.
# Provide a minimal object with a `gather` attribute pointing to
# `asyncio.gather` so tests can monkeypatch it.
class _TqdmAsyncioCompat:
    gather = staticmethod(asyncio.gather)

tqdm_asyncio = _TqdmAsyncioCompat()


def configure_logging(level: str = "INFO", enable_file: bool = True) -> None:
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)
    handlers = [logging.StreamHandler()]
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


def log_processing_summary(stats: dict, md_dir: Path, json_dir: Path) -> None:
    """Log a short summary about processed files and output directories.

    Kept as a top-level helper so legacy tests can call it directly.
    """
    try:
        total = int(stats.get("total_files_in_input_dir", 0))
        skipped = int(stats.get("skipped_already_processed", 0))
        attempted = int(stats.get("attempted_to_process", 0))
        success = int(stats.get("successful_ai_processing", 0))
        failed = int(stats.get("failed_ai_processing", 0))

        logger.info(
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
                logger.info("Markdown outputs: %d files in %s", len(md_files), md_dir)
            except Exception:
                logger.exception("Failed to list markdown output dir %s", md_dir)

        if json_dir.exists():
            try:
                json_files = [p for p in json_dir.iterdir() if p.is_file()]
                logger.info(
                    "Raw JSON responses: %d files in %s", len(json_files), json_dir
                )
            except Exception:
                logger.exception("Failed to list json output dir %s", json_dir)
    except Exception:
        logger.exception("Error while summarizing processing stats")


def parse_arguments() -> argparse.Namespace:
    import os

    parser = argparse.ArgumentParser(
        description="Process school description markdown files through an AI API."
    )
    parser.add_argument("-l", "--limit", type=int, default=None)
    parser.add_argument(
        "-i", "--input", type=str, default=str(DEFAULT_INPUT_MARKDOWN_DIR)
    )
    parser.add_argument(
        "-o", "--output", type=str, default=str(DEFAULT_OUTPUT_BASE_DIR)
    )
    parser.add_argument(
        "--log-level", type=str, default=os.environ.get("LOG_LEVEL", "INFO")
    )
    parser.add_argument("--lang", type=str, default=os.environ.get("LANG_UI", "en"))
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    disable_file = bool(
        os.environ.get("DISABLE_FILE_LOGS") or os.environ.get("PYTEST_CURRENT_TEST")
    )
    configure_logging(args.log_level, enable_file=not disable_file)
    logger.info("Starting AI processor orchestration")
    try:
        # Ensure OpenAIConfig can locate the project's .env via PROJECT_ROOT
        # and preserve backward compatibility with tests that monkeypatch
        # a `PROJECT_ROOT` attribute on this module.
        if not hasattr(__import__(__name__), "PROJECT_ROOT"):
            # Expose PROJECT_ROOT on the module for tests that patch it.
            globals()["PROJECT_ROOT"] = PROJECT_ROOT
        cfg = OpenAIConfig()
        processor = SchoolDescriptionProcessor(cfg, Path(args.input), Path(args.output))
        stats = asyncio.run(processor.process_all_files(args.limit))
        logger.info(f"Processing finished. Stats: {stats}")
    except KeyboardInterrupt:
        # Gracefully handle user interrupt (legacy tests expect no hard kill)
        logger.warning("Processing interrupted by user (KeyboardInterrupt).")
    except Exception:
        logger.exception("Processing failed.")


if __name__ == "__main__":
    main()

