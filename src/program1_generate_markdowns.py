"""Program 1: Markdown generation from CSV.

This script reads school data from a CSV file and generates one markdown
file per school using a text template. All configuration and magic values
are imported from ``src.config``. The module is designed for clarity and
testability, and its helpers expose small, composable functionality.

Usage
-----
python program1_generate_markdowns.py --csv-path ... --template-path ... --output-dir ... [--log-level ...]

Notes
-----
All file operations use ``pathlib.Path`` and context managers. Logging is
configured at the module level and sends output both to console and a log file.
"""

import argparse
import csv
import logging
import re
from pathlib import Path

# Robust import for src.config
try:
    from src.config import (
        LOG_DIR,
        LOG_FILENAME_GENERATE_MARKDOWNS,
        LOG_FORMAT,
        MISSING_DATA_PLACEHOLDER,
        ORIGINAL_CSV_PATH,
        OUTPUT_MARKDOWN_DIR,
        SURVEY_YEAR_SUFFIXES_PREFERENCE,
        TEMPLATE_FILE_PATH,
    )
except ImportError:  # pragma: no cover - import fallback for direct script runs
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.config import (
        LOG_DIR,
        LOG_FILENAME_GENERATE_MARKDOWNS,
        LOG_FORMAT,
        MISSING_DATA_PLACEHOLDER,
        ORIGINAL_CSV_PATH,
        OUTPUT_MARKDOWN_DIR,
        SURVEY_YEAR_SUFFIXES_PREFERENCE,
        TEMPLATE_FILE_PATH,
    )

logger = logging.getLogger(__name__)


def configure_logging(log_level: str = "INFO", enable_file: bool = True) -> None:
    """Configure logging for the script.

    Parameters
    ----------
    log_level : str
        Logging level as a string (e.g., ``"INFO"``, ``"DEBUG"``).
    enable_file : bool
        If ``True``, add a file handler; otherwise only log to console.

    Returns
    -------
    None
        This function configures global logging handlers.
    """
    # Remove existing handlers to ensure our config takes effect
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if enable_file:
        try:
            LOG_DIR.mkdir(exist_ok=True)
            handlers.insert(
                0,
                logging.FileHandler(
                    LOG_DIR / LOG_FILENAME_GENERATE_MARKDOWNS, mode="a"
                ),
            )
        except Exception:
            pass
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format=LOG_FORMAT,
        handlers=handlers,
    )


def get_value_from_row(row: dict[str, str], column_key: str) -> str:
    """Retrieve and sanitize a value from a CSV row dictionary.

    Parameters
    ----------
    row : dict[str, str]
        Mapping of CSV header to cell value.
    column_key : str
        Exact header name to look up.

    Returns
    -------
    str
        The trimmed cell value, or the global missing-data placeholder if missing or ``"N/A"``.

    Examples
    --------
    >>> row = {"SchoolCode": "  123  ", "X": "N/A"}
    >>> get_value_from_row(row, "SchoolCode")
    '123'
    >>> get_value_from_row(row, "X")
    '[Data Saknas]'
    >>> get_value_from_row(row, "Unknown")
    '[Data Saknas]'
    """
    value = row.get(column_key)
    if value is None:
        return MISSING_DATA_PLACEHOLDER
    str_value = str(value).strip()
    if str_value == "" or str_value.upper() == "N/A":
        return MISSING_DATA_PLACEHOLDER
    return str_value


def extract_placeholders_from_template(template_content: str) -> list[str]:
    """Identify all unique placeholders in template text.

    Placeholders are expected in ``{Name}`` format, and may contain underscores
    or slashes.

    Parameters
    ----------
    template_content : str
        The template string containing placeholders.

    Returns
    -------
    list[str]
        Sorted list of unique placeholder names.

    Examples
    --------
    >>> tpl = "Hello {SchoolName}! Code: {SchoolCode}. {SurveyAnswerCategory_Math}"
    >>> extract_placeholders_from_template(tpl)
    ['SchoolCode', 'SchoolName', 'SurveyAnswerCategory_Math']
    """
    return sorted(set(re.findall(r"\{([a-zA-Z0-9_/]+)\}", template_content)))


def build_template_context(
    row: dict[str, str], template_placeholders: list[str]
) -> dict[str, str]:
    """Build the context dictionary for template rendering.

    Parameters
    ----------
    row : dict[str, str]
        Dictionary mapping CSV headers to values.
    template_placeholders : list[str]
        List of placeholder names to fill.

    Returns
    -------
    dict[str, str]
        Dictionary mapping placeholders to their resolved values.
    """
    context: dict[str, str] = {}
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
    row: dict[str, str], template_placeholders: list[str]
) -> str:
    """Determine which survey year to report based on available data.

    Parameters
    ----------
    row : dict[str, str]
        Dictionary mapping CSV headers to values.
    template_placeholders : list[str]
        List of placeholder names used in the template.

    Returns
    -------
    str
        The survey year string (e.g., ``"2023/2024"``) or the global missing-data placeholder.

    Examples
    --------
    >>> placeholders = ["SurveyAnswerCategory_Math", "SchoolCode"]
    >>> row = {
    ...     'SurveyAnswerCategory_Math_2023/2024': '85',
    ...     'SurveyAnswerCategory_Math_2022/2023': '80'
    ... }
    >>> determine_survey_year_for_report(row, placeholders)
    '2023/2024'
    >>> row2 = {'SurveyAnswerCategory_Math_2023/2024': '', 'SurveyAnswerCategory_Math_2022/2023': ''}
    >>> determine_survey_year_for_report(row2, placeholders)
    '[Data Saknas]'
    """
    for suffix in SURVEY_YEAR_SUFFIXES_PREFERENCE:
        for placeholder in template_placeholders:
            if placeholder.startswith("SurveyAnswerCategory"):
                csv_col = f"{placeholder}{suffix}"
                if get_value_from_row(row, csv_col) != MISSING_DATA_PLACEHOLDER:
                    return suffix.replace("_", "")
    return MISSING_DATA_PLACEHOLDER


def get_survey_answer_value(row: dict[str, str], placeholder: str) -> str:
    """Get the value for a survey answer placeholder, preferring the latest year.

    Parameters
    ----------
    row : dict[str, str]
        Dictionary mapping CSV headers to values.
    placeholder : str
        The survey answer placeholder base name (e.g., ``"SurveyAnswerCategory_Math"``).

    Returns
    -------
    str
        The best available value for the placeholder, or the global missing-data placeholder.

    Examples
    --------
    >>> row = {
    ...     'SurveyAnswerCategory_Read_2023/2024': '',
    ...     'SurveyAnswerCategory_Read_2022/2023': '72'
    ... }
    >>> get_survey_answer_value(row, 'SurveyAnswerCategory_Read')
    '72'
    """
    for year_suffix in SURVEY_YEAR_SUFFIXES_PREFERENCE:
        csv_column_name = f"{placeholder}{year_suffix}"
        data_value = get_value_from_row(row, csv_column_name)
        if data_value != MISSING_DATA_PLACEHOLDER:
            return data_value
    return MISSING_DATA_PLACEHOLDER


def render_template(template_content: str, context: dict[str, str]) -> str:
    """Replace placeholders in a template with context values.

    Numeric strings ending in ``.0`` are rendered without the decimal part.

    Parameters
    ----------
    template_content : str
        The template string containing placeholders like ``{SchoolName}``.
    context : dict[str, str]
        Mapping from placeholder names to replacement values.

    Returns
    -------
    str
        The rendered template string.

    Examples
    --------
    >>> tpl = 'Name: {SchoolName}, Code: {SchoolCode}, Score: {Score}'
    >>> ctx = {'SchoolName': 'Alpha', 'SchoolCode': 'A-01', 'Score': '10.0'}
    >>> render_template(tpl, ctx)
    'Name: Alpha, Code: A-01, Score: 10'
    >>> ctx2 = {'SchoolName': 'Beta'}
    >>> render_template(tpl, ctx2)  # Missing placeholders get the global placeholder
    'Name: Beta, Code: [Data Saknas], Score: [Data Saknas]'
    """

    def format_number_string(val: str) -> str:
        """Format numeric string ending in '.0' as integer string."""
        if not isinstance(val, str):
            return val  # pragma: no cover - defensive branch
        if re.fullmatch(r"-?\d+\.0", val):
            return str(int(float(val)))
        return val

    pattern = re.compile(r"\{([a-zA-Z0-9_/]+)\}")

    def replace_func(match: re.Match[str]) -> str:
        placeholder_name = match.group(1)
        value = context.get(placeholder_name, MISSING_DATA_PLACEHOLDER)
        return format_number_string(value)

    return pattern.sub(replace_func, template_content)


def load_template_and_placeholders(template_path: Path) -> tuple[str, list[str]]:
    """Load the template file and extract placeholders.

    Parameters
    ----------
    template_path : Path
        Path to the template file.

    Returns
    -------
    tuple[str, list[str]]
        The template content and the list of placeholder names.
    """
    with template_path.open("r", encoding="utf-8") as template_file:
        template_content = template_file.read()
    placeholders = extract_placeholders_from_template(template_content)
    if not placeholders:
        logger.error("No placeholders found in the template.")
        raise ValueError("No placeholders found in the template.")
    return template_content, placeholders


def process_csv_and_generate_markdowns(
    csv_path: Path, template_content: str, placeholders: list[str], output_dir: Path
) -> int:
    """Process the CSV file and generate markdown files for each school.

    Parameters
    ----------
    csv_path : Path
        Path to the semicolon-delimited CSV file.
    template_content : str
        The already-loaded template text.
    placeholders : list[str]
        Names of placeholders to fill in the template.
    output_dir : Path
        Directory to write the generated markdown files.

    Returns
    -------
    int
        Number of markdown files generated (skips rows without a SchoolCode).
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
            except OSError as error:
                logger.error(f"Error writing {output_path}: {error}")
    return processed_count


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments for the script, including language and log level.

    Returns
    -------
    argparse.Namespace
        Parsed arguments namespace with paths and settings.
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
    """Run the markdown generation pipeline from CLI arguments.

    This function coordinates argument parsing, logging configuration,
    template loading, CSV processing, and error handling.

    Returns
    -------
    None
        This function performs I/O and logs status to console and file.
    """
    args = parse_arguments()
    import os as _os

    disable_file = bool(
        _os.environ.get("DISABLE_FILE_LOGS") or _os.environ.get("PYTEST_CURRENT_TEST")
    )
    configure_logging(args.log_level, enable_file=not disable_file)
    logger.info("=" * 50)
    logger.info("Starting Program 1: Markdown Generation")
    logger.info("=" * 50)
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
    except FileNotFoundError as file_error:  # pragma: no cover - CLI error path
        logger.error(f"File not found: {file_error}")
    except Exception as exc:  # pragma: no cover - generic CLI error path
        logger.error(f"Unexpected error: {exc}", exc_info=True)


def flush_and_close_log_handlers() -> None:
    """Flush and close all logging handlers to ensure logs are written.

    Returns
    -------
    None
        Ensures that buffered log messages are persisted.
    """
    for handler in logging.root.handlers:
        try:
            handler.flush()
        except Exception:
            pass
        try:
            handler.close()
        except Exception:
            pass


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()
    flush_and_close_log_handlers()
