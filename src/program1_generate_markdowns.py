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
import logging
from pathlib import Path

# Robust import for src.config
try:
    from src.config import (
        LOG_DIR,
        LOG_FILENAME_GENERATE_MARKDOWNS,
        LOG_FORMAT,
        ORIGINAL_CSV_PATH,
        OUTPUT_MARKDOWN_DIR,
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
        ORIGINAL_CSV_PATH,
        OUTPUT_MARKDOWN_DIR,
        TEMPLATE_FILE_PATH,
    )

logger = logging.getLogger(__name__)

# Import SRP-responsibility modules and expose their helpers as thin
# adapters so tests and other modules can continue to import functions
# from this orchestrator module while the implementation lives in
# `src.pipeline.markdown_generator`.
from src.pipeline.markdown_generator.data_loader import (
    determine_survey_year_for_report as dl_determine_survey_year_for_report,
)
from src.pipeline.markdown_generator.data_loader import (
    get_survey_answer_value as dl_get_survey_answer_value,
)
from src.pipeline.markdown_generator.data_loader import (
    get_value_from_row as dl_get_value_from_row,
)
from src.pipeline.markdown_generator.processor import (
    build_template_context as pipeline_build_template_context,
)
from src.pipeline.markdown_generator.processor import (
    process_csv_and_generate_markdowns as pipeline_process_csv_and_generate_markdowns,
)
from src.pipeline.markdown_generator.templating import (
    extract_placeholders_from_template as dl_extract_placeholders_from_template,
)
from src.pipeline.markdown_generator.templating import (
    load_template_and_placeholders as dl_load_template_and_placeholders,
)
from src.pipeline.markdown_generator.templating import (
    render_template as dl_render_template,
)


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
    """Adapter to the shared data loader implementation.

    Kept as a thin wrapper for backward compatibility with existing tests
    and call sites that import this function from the top-level module.
    """
    return dl_get_value_from_row(row, column_key)


def extract_placeholders_from_template(template_content: str) -> list[str]:
    """Adapter to templating placeholder extractor."""
    return dl_extract_placeholders_from_template(template_content)


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
    # Delegate the full construction to the pipeline implementation.
    return pipeline_build_template_context(row, template_placeholders)


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
    return dl_determine_survey_year_for_report(row, template_placeholders)


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
    return dl_get_survey_answer_value(row, placeholder)


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
    return dl_render_template(template_content, context)


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
    return dl_load_template_and_placeholders(template_path)


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
    # Delegate to the pipeline processor implementation
    return pipeline_process_csv_and_generate_markdowns(
        csv_path, template_content, placeholders, output_dir
    )


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
