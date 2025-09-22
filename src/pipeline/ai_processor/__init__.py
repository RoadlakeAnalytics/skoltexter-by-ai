"""The ai_processor package provides headless AI-driven data transformation for pipeline automation.

This package acts as the core AI processing layer within the pipeline architecture. It encapsulates asynchronous API client logic, configuration parsing, and file handling utilities required for large-scale content generation and post-processing steps involving external AI services. Its public API is stable and intended for use by both high-level pipeline runners and test suites.

A limited number of lightweight compatibility helpers are provided for legacy modules, easing migration by preserving old import paths temporarily. Users are encouraged to depend directly on the concrete implementations documented below.

The package does not expose any user-facing commands or entrypoints; execution should always occur via orchestrators or dedicated scripts.

Modules exported
----------------
AIAPIClient
    The resilient asyncio-driven API client for interacting with AI services.
OpenAIConfig
    Pipeline configuration class for model and service endpoints.
SchoolDescriptionProcessor
    Orchestrates the transformation of raw/templated text into AI-generated markdown.
find_markdown_files, save_processed_files
    File system helpers supporting batch processing of result artifacts.

Examples
--------
Import the primary interface objects for integration:

>>> from src.pipeline.ai_processor import AIAPIClient, SchoolDescriptionProcessor, find_markdown_files
>>> client = AIAPIClient(OpenAIConfig(...))
>>> processor = SchoolDescriptionProcessor(client)
>>> files = find_markdown_files("data/markdown_inputs/")
>>> # Process files using your orchestrator logic...

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
