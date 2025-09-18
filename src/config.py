"""Global configuration constants for the project.

Defines paths and filenames used across the pipeline and setup utilities.
"""

from __future__ import annotations

from pathlib import Path

# Project directories
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
SRC_DIR: Path = PROJECT_ROOT / "src"
LOG_DIR: Path = PROJECT_ROOT / "logs"
VENV_DIR: Path = PROJECT_ROOT / "venv"

# Requirements
REQUIREMENTS_FILE: Path = PROJECT_ROOT / "requirements.txt"
REQUIREMENTS_LOCK_FILE: Path = PROJECT_ROOT / "requirements.lock"

# AI / Azure defaults and filenames used across the pipeline
DEFAULT_API_VERSION: str = "2024-05-01-preview"
DEFAULT_DEPLOYMENT_NAME: str = "gpt-4o"

# AI processed filenames and directories
AI_PROCESSED_FILENAME_SUFFIX: str = ".processed.md"
AI_PROCESSED_MARKDOWN_SUBDIR: str = "processed_markdowns"
AI_RAW_RESPONSE_FILENAME_SUFFIX: str = ".raw.json"
AI_RAW_RESPONSES_SUBDIR: str = "raw_responses"
AI_FAILED_RESPONSE_FILENAME_SUFFIX: str = ".failed.json"

# Prompt/template paths (relative to project root)
AI_PROMPT_TEMPLATE_PATH: str = str(
    PROJECT_ROOT / "templates" / "ai_prompt_template.txt"
)

# AI payload defaults
AI_PAYLOAD_MAX_TOKENS: int = 1024

# CSV / templating defaults
MISSING_DATA_PLACEHOLDER: str = "[Data Saknas]"
SURVEY_YEAR_SUFFIXES_PREFERENCE: list[str] = ["_2023/2024", "_2022/2023"]

# Website generation defaults
FALLBACK_SCHOOL_NAME_FORMAT: str = "School {school_code}"
FALLBACK_DESCRIPTION_HTML: str = "<p>Description not available.</p>"
ERROR_DESCRIPTION_HTML: str = "<p>Error loading description.</p>"

# CLI defaults and logging
DEFAULT_INPUT_MARKDOWN_DIR: Path = PROJECT_ROOT / "input_markdowns"
DEFAULT_OUTPUT_BASE_DIR: Path = PROJECT_ROOT / "output"
LOG_FILENAME_AI_PROCESSOR: str = "ai_processor.log"
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Backwards-compatible defaults for legacy entrypoint scripts
LOG_FILENAME_GENERATE_MARKDOWNS: str = "generate_markdowns.log"
ORIGINAL_CSV_PATH: Path = PROJECT_ROOT / "data" / "schools.csv"
TEMPLATE_FILE_PATH: Path = PROJECT_ROOT / "templates" / "school_description_template.md"
OUTPUT_MARKDOWN_DIR: Path = PROJECT_ROOT / "output" / "markdowns"

# Website generation defaults
AI_MARKDOWN_DIR: Path = PROJECT_ROOT / "output" / "processed_markdowns"
LOG_FILENAME_GENERATE_WEBSITE: str = "generate_website.log"
NO_DATA_HTML: str = "<html><body><h1>No school data available</h1></body></html>"
OUTPUT_HTML_FILE: Path = PROJECT_ROOT / "output" / "index.html"
WEBSITE_TEMPLATE_PATH: Path = PROJECT_ROOT / "templates" / "website_template.html"

# UI defaults
LANG: str = "en"
