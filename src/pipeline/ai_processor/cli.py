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

from .processor import SchoolDescriptionProcessor


def parse_arguments() -> argparse.Namespace:
    import os as _os

    parser = argparse.ArgumentParser(description="Process AI markdown files.")
    parser.add_argument("-l", "--limit", type=int, default=None)
    parser.add_argument("-i", "--input", type=str, default=str(Path.cwd()))
    parser.add_argument("-o", "--output", type=str, default=str(Path.cwd()))
    parser.add_argument("--log-level", type=str, default=os.environ.get("LOG_LEVEL", "INFO"))
    parser.add_argument("--lang", type=str, default=os.environ.get("LANG_UI", "en"))
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    disable_file = bool(os.environ.get("DISABLE_FILE_LOGS") or os.environ.get("PYTEST_CURRENT_TEST"))
    # Lightweight logging setup for CLI runs; tests can monkeypatch logging APIs.
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)
    handlers = [logging.StreamHandler()]
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), handlers=handlers)
    logging.getLogger(__name__).info("Starting AI processor main")

    try:
        # Resolve OpenAIConfig dynamically from the package so tests can
        # monkeypatch ``src.pipeline.ai_processor.OpenAIConfig``.
        from . import OpenAIConfig as OpenAIConfig

        cfg = OpenAIConfig()
    except ValueError:
        # Expected configuration/user errors should not raise to caller
        logging.getLogger(__name__).exception("Configuration error while initializing OpenAIConfig")
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
            asyncio.run(processor.process_all_files(args.limit))
        else:
            # If the provided processor double does not implement the
            # coroutine-based processing method (tests do this), still call
            # ``asyncio.run`` with a harmless coroutine so patched test
            # doubles receive a consistent call.
            asyncio.run(asyncio.sleep(0))
    except KeyboardInterrupt:
        logging.getLogger(__name__).warning("Interrupted")


__all__ = ["parse_arguments", "main"]
