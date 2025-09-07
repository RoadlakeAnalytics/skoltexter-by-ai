"""Configuration constants for the School Data Processing Project.

This module centralizes all magic values, default paths, filenames, suffixes, and thresholds
used across the project's scripts. All constants are UPPERCASE, use type hints, and are
documented below for clarity and maintainability.

Constants:

- PROJECT_ROOT (Path): Absolute path to the project root directory.
- SRC_DIR (Path): Path to the 'src' directory.
- DATA_DIR (Path): Path to the 'data' directory.
- LOG_DIR (Path): Path to the 'logs' directory.
- VENV_DIR (Path): Path to the Python virtual environment directory.
- REQUIREMENTS_FILE (Path): Path to 'requirements.txt'.

Program 1: Markdown Generation
- ORIGINAL_CSV_PATH (Path): Path to the main school data CSV file.
- TEMPLATE_FILE_PATH (Path): Path to the markdown template file.
- OUTPUT_MARKDOWN_DIR (Path): Directory for generated markdown files.
- MISSING_DATA_PLACEHOLDER (str): Placeholder string for missing data in templates.
- SURVEY_YEAR_SUFFIXES_PREFERENCE (list[str]): Suffixes for survey year columns, in preference order.

Program 2: AI Processor
- AI_PROCESSED_MARKDOWN_SUBDIR (str): Subdirectory for AI-processed markdown files.
- AI_RAW_RESPONSES_SUBDIR (str): Subdirectory for raw AI JSON responses.
- AI_PROCESSED_FILENAME_SUFFIX (str): Suffix for AI-processed markdown filenames.
- AI_RAW_RESPONSE_FILENAME_SUFFIX (str): Suffix for raw AI response JSON filenames.
- AI_FAILED_RESPONSE_FILENAME_SUFFIX (str): Suffix for failed AI response JSON filenames.
- DEFAULT_INPUT_MARKDOWN_DIR (Path): Default input directory for markdown files.
- DEFAULT_OUTPUT_BASE_DIR (Path): Default output directory for AI-processed files.
- AI_PROMPT_TEMPLATE_PATH (Path): Path to the AI prompt template file.
- MAX_CONCURRENT_REQUESTS (int): Default maximum concurrent API requests.
- TARGET_RPM (int): Default target requests per minute for rate limiting.
- MAX_RETRIES (int): Default maximum number of API retries.
- BACKOFF_FACTOR (float): Exponential backoff factor for retries.
- RETRY_SLEEP_ON_429 (int): Seconds to sleep on HTTP 429 (rate limit) errors.
- TEMPERATURE (float): Default temperature for AI completions.
- REQUEST_TIMEOUT (int): Default request timeout in seconds.
- DEFAULT_DEPLOYMENT_NAME (str): Default Azure OpenAI deployment name.
- DEFAULT_API_VERSION (str): Default Azure OpenAI API version.
- AI_PAYLOAD_MAX_TOKENS (int): Maximum tokens for AI completion payloads.

Program 3: Website Generation
- AI_MARKDOWN_DIR (Path): Directory containing AI-processed markdown files.
- OUTPUT_HTML_DIR (Path): Directory for generated HTML files.
- OUTPUT_HTML_FILE (Path): Path to the generated HTML file.
- WEBSITE_TEMPLATE_PATH (Path): Path to the website HTML template file.
- FALLBACK_SCHOOL_NAME_FORMAT (str): Format string for fallback school name.
- FALLBACK_DESCRIPTION_HTML (str): HTML shown when no description is available.
- ERROR_DESCRIPTION_HTML (str): HTML shown when an error occurs loading description.
- NO_DATA_HTML (str): Minimal HTML page shown when no school data is available.

Logging
- LOG_FORMAT (str): Format string for logging.
- LOG_FILENAME_GENERATE_MARKDOWNS (str): Log filename for Program 1.
- LOG_FILENAME_AI_PROCESSOR (str): Log filename for Program 2.
- LOG_FILENAME_GENERATE_WEBSITE (str): Log filename for Program 3.

setup_project.py
- LANG (str): Default UI language ("en").

"""

from pathlib import Path

# --- Project-wide Paths ---
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
SRC_DIR: Path = PROJECT_ROOT / "src"
DATA_DIR: Path = PROJECT_ROOT / "data"
LOG_DIR: Path = PROJECT_ROOT / "logs"
VENV_DIR: Path = PROJECT_ROOT / "venv"
REQUIREMENTS_FILE: Path = PROJECT_ROOT / "requirements.txt"

# --- Program 1: Markdown Generation ---
ORIGINAL_CSV_PATH: Path = DATA_DIR / "database_data" / "database_school_data.csv"
TEMPLATE_FILE_PATH: Path = DATA_DIR / "templates" / "school_description_template.md"
OUTPUT_MARKDOWN_DIR: Path = DATA_DIR / "generated_markdown_from_csv"
MISSING_DATA_PLACEHOLDER: str = "[Data Saknas]"
SURVEY_YEAR_SUFFIXES_PREFERENCE: list[str] = ["_2023/2024", "_2022/2023"]

# --- Program 2: AI Processor ---
AI_PROCESSED_MARKDOWN_SUBDIR: str = "ai_processed_markdown"
AI_RAW_RESPONSES_SUBDIR: str = "ai_raw_responses"
AI_PROCESSED_FILENAME_SUFFIX: str = "_ai_description.md"
AI_RAW_RESPONSE_FILENAME_SUFFIX: str = "_gpt4o_response.json"
AI_FAILED_RESPONSE_FILENAME_SUFFIX: str = "_gpt4o_FAILED_response.json"
DEFAULT_INPUT_MARKDOWN_DIR: Path = DATA_DIR / "generated_markdown_from_csv"
DEFAULT_OUTPUT_BASE_DIR: Path = DATA_DIR
AI_PROMPT_TEMPLATE_PATH: Path = DATA_DIR / "templates" / "ai_prompt_template.txt"
MAX_CONCURRENT_REQUESTS: int = 250
TARGET_RPM: int = 10000
MAX_RETRIES: int = 3
BACKOFF_FACTOR: float = 2.0
RETRY_SLEEP_ON_429: int = 60
TEMPERATURE: float = 0.10
REQUEST_TIMEOUT: int = 300
DEFAULT_DEPLOYMENT_NAME: str = "gpt-4o"
DEFAULT_API_VERSION: str = "2024-05-01-preview"
AI_PAYLOAD_MAX_TOKENS: int = 2048

# --- Program 3: Website Generation ---
AI_MARKDOWN_DIR: Path = DATA_DIR / AI_PROCESSED_MARKDOWN_SUBDIR
OUTPUT_HTML_DIR: Path = PROJECT_ROOT / "output"
OUTPUT_HTML_FILE: Path = OUTPUT_HTML_DIR / "index.html"
WEBSITE_TEMPLATE_PATH: Path = DATA_DIR / "templates" / "website_template.html"
FALLBACK_SCHOOL_NAME_FORMAT: str = "School (Code: {school_code})"
FALLBACK_DESCRIPTION_HTML: str = (
    "<p><em>Description not available for this school.</em></p>"
)
ERROR_DESCRIPTION_HTML: str = "<p><em>Error loading description.</em></p>"
NO_DATA_HTML: str = (
    '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
    "<title>School Information</title>"
    "<style>body{font-family: sans-serif; text-align: center; padding: 50px;}</style></head>"
    "<body><h1>School Information</h1><p>No school data is available to display.</p></body></html>"
)

# --- Logging ---
LOG_FORMAT: str = (
    "%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s"
)
LOG_FILENAME_GENERATE_MARKDOWNS: str = "generate_markdowns.log"
LOG_FILENAME_AI_PROCESSOR: str = "ai_processor.log"
LOG_FILENAME_GENERATE_WEBSITE: str = "generate_website.log"

# --- setup_project.py ---
LANG: str = "en"
