"""AI processor package.

This package isolates API client logic, configuration loading and file
handling for AI processing.
"""

from .client import AIAPIClient
from .config import OpenAIConfig
from .file_handler import find_markdown_files, save_processed_files
from .processor import SchoolDescriptionProcessor

__all__ = [
    "OpenAIConfig",
    "AIAPIClient",
    "find_markdown_files",
    "save_processed_files",
    "SchoolDescriptionProcessor",
]
