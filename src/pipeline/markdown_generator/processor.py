"""Markdown generation processing module.

Transforms school CSV data into per-school markdown files for the static site pipeline.
This module operates as a headless data layer, responsible solely for context construction,
template rendering, error logging, and strict separation from orchestration/UI logic.

Responsibilities
----------------
- Build template contexts from tabular school data and survey answers.
- Render and write one markdown file per school, named by school code.
- Log all missing data, skipped rows, and file I/O errors for robust auditability.

See Also
--------
src/pipeline/markdown_generator/data_loader.py
src/pipeline/markdown_generator/templating.py
AGENTS.md: Coding & Documentation Standards

Notes
-----
All exceptions follow taxonomy set in src/exceptions.py and AGENTS.md.
No business logic, retries, or concurrency are handled here.

References
----------
.. [1] AGENTS.md: AI Coding & Project Standards: School Data Pipeline

Examples
--------
>>> from src.pipeline.markdown_generator.processor import process_csv_and_generate_markdowns
>>> from pathlib import Path
>>> process_csv_and_generate_markdowns(
...     Path("schools.csv"),
...     "# {SchoolCode}\\nYear: {SurveySchoolYear}\\n",
...     ["SchoolCode", "SurveySchoolYear"],
...     Path("out_md")
... )
# Produces per-school markdown files in 'out_md'

"""

import logging
from pathlib import Path

from src.config import MISSING_DATA_PLACEHOLDER

from .data_loader import (
    determine_survey_year_for_report,
    get_survey_answer_value,
    get_value_from_row,
    load_school_rows_from_csv,
)
from .templating import render_template

logger = logging.getLogger(__name__)


def build_template_context(
    row: dict[str, str], template_placeholders: list[str]
) -> dict[str, str]:
    """Construct mapping from template placeholders to resolved school row values.

    This function creates the context required to render a markdown template for a single school.
    It resolves every required field, including 'SchoolCode' and 'SurveySchoolYear', and any fields
    referenced by the template. "SurveyAnswerCategory" placeholders are handled by data loader helpers.

    Parameters
    ----------
    row : dict[str, str]
        Dictionary representing a school survey row. Must include "SchoolCode".
    template_placeholders : list[str]
        List of placeholder names required by the markdown template.

    Returns
    -------
    dict[str, str]
        Dictionary mapping each placeholder to its resolved string value for rendering.

    Raises
    ------
    KeyError
        If required direct fields are missing, i.e., not present in the row.
    DataValidationError
        If schema validation in helpers fails.

    See Also
    --------
    src/pipeline/markdown_generator/data_loader.py

    Notes
    -----
    'SchoolCode' and 'SurveySchoolYear' are always resolved and included.
    Missing values may be replaced by MISSING_DATA_PLACEHOLDER.

    References
    ----------
    .. [1] AGENTS.md: Docstring and robustness gold standard.

    Examples
    --------
        >>> sample = {"SchoolCode": "001", "SurveySchoolYear": "2023", "Other": "foo"}
        >>> placeholders = ["SchoolCode", "SurveySchoolYear", "Other"]
        >>> ctx = build_template_context(sample, placeholders)
        >>> assert ctx["SchoolCode"] == "001"
        >>> assert ctx["Other"] == "foo"
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


def process_csv_and_generate_markdowns(
    csv_path: Path, template_content: str, placeholders: list[str], output_dir: Path
) -> int:
    """Process a school CSV and write a markdown file for each valid school row.

    Reads all school rows from the source CSV, builds the template context, and writes
    Markdown output per school. Skips rows missing a school code and logs any skipped or error events.
    File write errors are logged but do not halt processing of subsequent rows.

    Parameters
    ----------
    csv_path : Path
        Path to the input CSV containing school and survey data.
    template_content : str
        Markdown template string to render for each school.
    placeholders : list[str]
        List of variable names required by the template.
    output_dir : Path
        Output directory for the written markdown files.

    Returns
    -------
    int
        Number of successful markdown files generated.

    Raises
    ------
    DataValidationError
        If the CSV is missing required structural columns.
    OSError
        If output file writing fails due to system error.

    See Also
    --------
    build_template_context
    src/config.py: Configuration constants

    Notes
    -----
    Rows lacking SchoolCode are skipped and logged. Output files are named "{SchoolCode}.md".
    All errors and skipped events are logged for compliance and forensic debugging.

    References
    ----------
    .. [1] AGENTS.md: Robustness Rules, Documentation

    Examples
    --------
        >>> from src.pipeline.markdown_generator.processor import process_csv_and_generate_markdowns
        >>> from pathlib import Path
        >>> csv_path = Path("schools.csv")
        >>> template = "# {SchoolCode}\\nYear: {SurveySchoolYear}\\n"
        >>> out_dir = Path("out_md")
        >>> n = process_csv_and_generate_markdowns(csv_path, template, ["SchoolCode", "SurveySchoolYear"], out_dir)
        >>> isinstance(n, int)
        True
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    processed_count = 0
    for row_number, row in enumerate(load_school_rows_from_csv(csv_path), start=2):
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
