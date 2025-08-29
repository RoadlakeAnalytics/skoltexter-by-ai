"""Program 1: Markdown generation from CSV.

This script reads school data from a CSV file and generates markdown files for each school
using a template. All configuration and magic values are imported from config.py.

Usage:
    python program1_generate_markdowns.py --csv-path ... --template-path ... --output-dir ... [--log-level ...]

All file operations use pathlib.Path and context managers. Logging is configured at the module level.
"""

import argparse
import csv
import logging
import re
from pathlib import Path
from typing import List, Dict

# Robust import for src.config
try:
    from src.config import (
        ORIGINAL_CSV_PATH,
        TEMPLATE_FILE_PATH,
        OUTPUT_MARKDOWN_DIR,
        MISSING_DATA_PLACEHOLDER,
        SURVEY_YEAR_SUFFIXES_PREFERENCE,
        LOG_DIR,
        LOG_FORMAT,
        LOG_FILENAME_GENERATE_MARKDOWNS,
    )
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.config import (
        ORIGINAL_CSV_PATH,
        TEMPLATE_FILE_PATH,
        OUTPUT_MARKDOWN_DIR,
        MISSING_DATA_PLACEHOLDER,
        SURVEY_YEAR_SUFFIXES_PREFERENCE,
        LOG_DIR,
        LOG_FORMAT,
        LOG_FILENAME_GENERATE_MARKDOWNS,
    )

logger = logging.getLogger(__name__)


def configure_logging(log_level: str = "INFO") -> None:
    """Configure logging for the script.

    Args:
        log_level: Logging level as a string (e.g., "INFO", "DEBUG").
    """
    LOG_DIR.mkdir(exist_ok=True)
    # Remove all existing handlers to ensure our config takes effect
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(LOG_DIR / LOG_FILENAME_GENERATE_MARKDOWNS, mode="a"),
            logging.StreamHandler(),
        ],
    )


def get_value_from_row(row: Dict[str, str], column_key: str) -> str:
    """Retrieve and sanitize a value from a CSV row dictionary.

    Args:
        row: Mapping of CSV header to cell value.
        column_key: Exact header name to look up.

    Returns:
        The trimmed cell value, or placeholder if missing or 'N/A'.
    """
    value = row.get(column_key)
    if value is None:
        return MISSING_DATA_PLACEHOLDER
    str_value = str(value).strip()
    if str_value == "" or str_value.upper() == "N/A":
        return MISSING_DATA_PLACEHOLDER
    return str_value


def extract_placeholders_from_template(template_content: str) -> List[str]:
    """Identify all unique placeholders in template text.

    Placeholders are expected in {Name} format, including underscores or slashes.

    Args:
        template_content: The template string.

    Returns:
        Sorted list of unique placeholder names.
    """
    return sorted(set(re.findall(r"\{([a-zA-Z0-9_/]+)\}", template_content)))


def build_template_context(
    row: Dict[str, str], template_placeholders: List[str]
) -> Dict[str, str]:
    """Build the context dictionary for template rendering.

    Args:
        row: Dictionary mapping CSV headers to values.
        template_placeholders: List of placeholders to fill.

    Returns:
        Dictionary mapping placeholders to values.
    """
    context: Dict[str, str] = {}
    context["SchoolCode"] = get_value_from_row(row, "SchoolCode")
    context["SurveySchoolYear"] = determine_survey_year_for_report(
        row, template_placeholders
    )
    for placeholder in template_placeholders:
        if placeholder in context:
            continue
        if placeholder.startswith("SurveyAnswerCategory"):
            context[placeholder] = get_survey_answer_value(row, placeholder)
        else:
            context[placeholder] = get_value_from_row(row, placeholder)
    return context


def determine_survey_year_for_report(
    row: Dict[str, str], template_placeholders: List[str]
) -> str:
    """Determine which survey year to report based on available data.

    Args:
        row: Dictionary mapping CSV headers to values.
        template_placeholders: List of placeholders to check.

    Returns:
        The survey year string or missing data placeholder.
    """
    for suffix in SURVEY_YEAR_SUFFIXES_PREFERENCE:
        for placeholder in template_placeholders:
            if placeholder.startswith("SurveyAnswerCategory"):
                csv_col = f"{placeholder}{suffix}"
                if get_value_from_row(row, csv_col) != MISSING_DATA_PLACEHOLDER:
                    return suffix.replace("_", "")
    return MISSING_DATA_PLACEHOLDER


def get_survey_answer_value(row: Dict[str, str], placeholder: str) -> str:
    """Get the value for a survey answer placeholder, preferring the latest year.

    Args:
        row: Dictionary mapping CSV headers to values.
        placeholder: The survey answer placeholder name.

    Returns:
        The value for the placeholder or missing data placeholder.
    """
    for year_suffix in SURVEY_YEAR_SUFFIXES_PREFERENCE:
        csv_column_name = f"{placeholder}{year_suffix}"
        data_value = get_value_from_row(row, csv_column_name)
        if data_value != MISSING_DATA_PLACEHOLDER:
            return data_value
    return MISSING_DATA_PLACEHOLDER


def render_template(template_content: str, context: Dict[str, str]) -> str:
    """Replace placeholders in template with context values.

    Numeric strings ending in '.0' are rendered without decimal part.

    Args:
        template_content: The template string.
        context: Dictionary mapping placeholders to values.

    Returns:
        The rendered template string.
    """

    def format_number_string(val: str) -> str:
        """Format numeric string ending in '.0' as integer string."""
        if not isinstance(val, str):
            return val
        if re.fullmatch(r"-?\d+\.0", val):
            return str(int(float(val)))
        return val

    pattern = re.compile(r"\{([a-zA-Z0-9_/]+)\}")

    def replace_func(match: re.Match) -> str:
        placeholder_name = match.group(1)
        value = context.get(placeholder_name, MISSING_DATA_PLACEHOLDER)
        return format_number_string(value)

    return pattern.sub(replace_func, template_content)


def load_template_and_placeholders(template_path: Path) -> tuple[str, List[str]]:
    """Load the template file and extract placeholders.

    Args:
        template_path: Path to the template file.

    Returns:
        Tuple of template content and list of placeholders.
    """
    with template_path.open("r", encoding="utf-8") as template_file:
        template_content = template_file.read()
    placeholders = extract_placeholders_from_template(template_content)
    if not placeholders:
        logger.error("No placeholders found in the template.")
        raise ValueError("No placeholders found in the template.")
    return template_content, placeholders


def process_csv_and_generate_markdowns(
    csv_path: Path, template_content: str, placeholders: List[str], output_dir: Path
) -> int:
    """Process the CSV file and generate markdown files for each school.

    Args:
        csv_path: Path to the CSV file.
        template_content: The template string.
        placeholders: List of placeholders to fill.
        output_dir: Directory to write markdown files.

    Returns:
        Number of markdown files generated.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    processed_count = 0
    with csv_path.open("r", encoding="utf-8-sig") as csvfile:
        header_line = csvfile.readline()
        if not header_line:
            logger.error(f"CSV missing header: {csv_path}")
            return 0
        headers = [header.strip('"') for header in header_line.strip().split(";")]
        reader = csv.DictReader(csvfile, fieldnames=headers, delimiter=";")
        for row_number, raw_row in enumerate(reader, start=2):
            row = {key: str(value).strip('"') for key, value in raw_row.items()}
            school_code = get_value_from_row(row, "SchoolCode")
            if school_code == MISSING_DATA_PLACEHOLDER:
                logger.warning(f"Row {row_number}: missing SchoolCode, skipping.")
                continue
            context = build_template_context(row, placeholders)
            output_content = render_template(template_content, context)
            output_path = output_dir / f"{school_code}.md"
            try:
                with output_path.open("w", encoding="utf-8") as output_file:
                    output_file.write(output_content)
                processed_count += 1
            except IOError as error:
                logger.error(f"Error writing {output_path}: {error}")
    return processed_count


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments for the script, including language and log level.

    Returns:
        Parsed arguments namespace.
    """
    import os

    parser = argparse.ArgumentParser(
        description="Generate markdown files from school CSV data."
    )
    parser.add_argument(
        "--csv-path",
        type=Path,
        default=ORIGINAL_CSV_PATH,
        help="Path to the input CSV file.",
    )
    parser.add_argument(
        "--template-path",
        type=Path,
        default=TEMPLATE_FILE_PATH,
        help="Path to the markdown template file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_MARKDOWN_DIR,
        help="Directory to write generated markdown files.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=os.environ.get("LOG_LEVEL", "INFO"),
        help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default=os.environ.get("LANG_UI", "en"),
        help="Language code for output/logs (en or sv).",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for markdown generation from CSV."""
    args = parse_arguments()
    configure_logging(args.log_level)
    logger.info("="*50)
    logger.info("Starting Program 1: Markdown Generation")
    logger.info("="*50)
    # Language argument is accepted for future-proofing; not used in this script
    logger.info(
        f"Starting markdown generation using CSV: {args.csv_path}, template: {args.template_path}, output: {args.output_dir} (lang={args.lang})"
    )
    try:
        template_content, placeholders = load_template_and_placeholders(
            args.template_path
        )
        processed_count = process_csv_and_generate_markdowns(
            args.csv_path, template_content, placeholders, args.output_dir
        )
        logger.info(f"Done: {processed_count} files generated.")
    except FileNotFoundError as file_error:
        logger.error(f"File not found: {file_error}")
    except Exception as exc:
        logger.error(f"Unexpected error: {exc}", exc_info=True)


def flush_and_close_log_handlers() -> None:
    """Flush and close all logging handlers to ensure logs are written."""
    for handler in logging.root.handlers:
        try:
            handler.flush()
        except Exception:
            pass
        try:
            handler.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
    flush_and_close_log_handlers()