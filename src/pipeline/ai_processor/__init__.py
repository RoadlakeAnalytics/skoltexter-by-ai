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

from .client import AIAPIClient
from .config import OpenAIConfig
from .file_handler import find_markdown_files, save_processed_files
from .processor import SchoolDescriptionProcessor

__all__ = [
    "AIAPIClient",
    "OpenAIConfig",
    "SchoolDescriptionProcessor",
    "find_markdown_files",
    "save_processed_files",
]
