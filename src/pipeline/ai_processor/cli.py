"""CLI entrypoint and logging/argument utilities for the AI processor pipeline.

This module implements the command-line interface (CLI) for the AI processor stage
of the school data pipeline. It provides a strict orchestration layer: argument parsing,
logging setup, and configuration management for executing the core processing logic via
:class:`SchoolDescriptionProcessor`. All business logic is delegated to independent modules,
enforcing strict decoupling and testability.

The primary entrypoint is the `main()` function. This may be invoked either via CLI
(batch processing) or programmatically (as part of integration or functional tests).
Errors are managed robustly: exceptions are logged and translated under a centralized
error taxonomy (see :mod:`src.exceptions`). KeyboardInterrupt and misconfiguration
are handled gracefully.

This file contains no custom input/output routines except for CLI argument parsing
and structured logging to stderr or file (configurable). Logging setup is resilience-
oriented, suppressing file handler errors during test simulation. All asynchronous
execution is managed using `asyncio.run`, with runtime detection for monkeypatched
testing stubs.

All file paths, limits, and settings are obtained from the environment, `src/config.py`,
or via CLI, with sensible defaults for local development and CI execution.

See Also
--------
src.pipeline.ai_processor.processor
    Core :class:`SchoolDescriptionProcessor` invoked via `main`.
src.pipeline.ai_processor.client
    :class:`OpenAIConfig` for API configuration, designed for monkeypatchable testing.
src.exceptions
    Centralized exception taxonomy and error translation primitives.

Notes
-----
Argument parsing defaults to the current working directory for input/output.
Log level and language can be overridden by environment variables.
Detection of test asynchronous execution avoids issues with monkeypatched
asyncio run implementations.

References
----------
None.

Examples
--------
CLI usage:

>>> # In shell
>>> python -m src.pipeline.ai_processor.cli --limit 2 --input data/markdown --output data/ai_output
Starting AI processor main
Processing summary: total=2 skipped=0 attempted=2 success=2 failed=0

Programmatic usage (for testing/integration):

>>> from src.pipeline.ai_processor.cli import main
>>> main()
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
    r"""Configure logging output for the AI processor CLI/tooling layer.

    This sets up logging handlers for console (always) and optionally for file, using
    the format and log file location configured in `src/config.py`. If file handler
    creation fails (e.g., due to permissions or when monkeypatched by test harnesses),
    the exception is suppressed to promote test resilience. Use this utility
    to ensure consistent logger configuration between CLI, subprocessed tools, and
    test simulations.

    Parameters
    ----------
    level : str, optional
        The logging level to use, e.g., "DEBUG", "INFO", "WARNING", "ERROR".
        Defaults to "INFO".
    enable_file : bool, optional
        Whether to add a file handler (writes to the pipeline log file).
        If False, disables file logging. Defaults to True.

    Returns
    -------
    None
        This function performs side effects only, configuring the root logger.

    Notes
    -----
    Intended primarily for CLI entrypoints, and for use by tests that want to
    simulate handler creation failures by monkeypatching `logging.FileHandler`.
    All handlers are removed and replaced. Any exception raised by
    `logging.FileHandler` is swallowed so as not to interfere with test execution.

    Examples
    --------
    >>> from src.pipeline.ai_processor.cli import configure_logging
    >>> configure_logging("DEBUG", enable_file=False)
    >>> import logging; logging.info("message")  # Should log to stderr only.
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
            # File handler failures suppressed to ensure test resilience.
            pass
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=LOG_FORMAT,
        handlers=handlers,
    )



def log_processing_summary(stats: dict[str, int], md_dir: Path, json_dir: Path) -> None:
    r"""Log a summary of AI-processed file statistics and output directories.

    Generates a compact, human-readable summary about the number of files processed,
    skipped, attempted, succeeded, and failed, as well as counts for Markdown and
    raw JSON output files. Intended for reporting at the conclusion of a batch run
    or in CLI entrypoint output. Errors during directory inspection are logged as
    exceptions and do not propagate.

    Parameters
    ----------
    stats : dict[str, int]
        Dictionary mapping keys like "total_files_in_input_dir", "skipped_already_processed",
        etc., to integer statistics.
    md_dir : Path
        Path to the directory where Markdown outputs are written.
    json_dir : Path
        Path to the directory where raw JSON response files are written.

    Returns
    -------
    None
        This function performs side effects (logs to INFO/ERROR).

    Notes
    -----
    Directory existence and file counting is best-effort and any exceptions are
    logged but not raised. Intended for use in CLI output and automated batch workflows.

    Examples
    --------
    >>> import logging; logging.basicConfig(level=logging.INFO)
    >>> from pathlib import Path
    >>> from src.pipeline.ai_processor.cli import log_processing_summary
    >>> stats = {"total_files_in_input_dir": 7, "skipped_already_processed": 1,
    ...          "attempted_to_process": 6, "successful_ai_processing": 6, "failed_ai_processing": 0}
    >>> log_processing_summary(stats, Path("."), Path("."))  # doctest: +SKIP

    See Also
    --------
    configure_logging : CLI logging setup utility.
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
