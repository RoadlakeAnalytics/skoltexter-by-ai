"""Generate Markdown files from school CSV data.

Transforms rows from a schools CSV into per-school Markdown files by building
template contexts and rendering templates. This module focuses on data
transformation and file output and does not manage orchestration or UI.
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
    """Construct a mapping from template placeholders to resolved row values.

    Build the context required to render a markdown template for a single
    school. This resolves required fields such as ``SchoolCode`` and
    ``SurveySchoolYear`` and any additional placeholders used by the
    template. Placeholders prefixed with ``SurveyAnswerCategory`` are
    resolved using helper functions from the data loader.

    Parameters
    ----------
    row : dict[str, str]
        Dictionary representing a school survey row.
    template_placeholders : list[str]
        List of placeholder names required by the markdown template.

    Returns
    -------
    dict[str, str]
        Dictionary mapping each placeholder to its resolved string value.

    Raises
    ------
    KeyError
        If a required direct field is missing from ``row``.
    src.exceptions.DataValidationError
        If schema validation in helper functions fails.

    Notes
    -----
    Missing values may be replaced by ``MISSING_DATA_PLACEHOLDER``.

    Examples
    --------
    >>> sample = {"SchoolCode": "001", "SurveySchoolYear": "2023", "Other": "foo"}
    >>> placeholders = ["SchoolCode", "SurveySchoolYear", "Other"]
    >>> ctx = build_template_context(sample, placeholders)
    >>> ctx["SchoolCode"] == "001"
    True
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
    """Process a school CSV and write a markdown file for each valid row.

    Reads rows from the source CSV, builds the template context for each row,
    renders the markdown content, and writes one file per school. Rows missing a
    school code are skipped and logged; file write errors are logged and
    processing continues for subsequent rows.

    Parameters
    ----------
    csv_path : Path
        Path to the input CSV containing school and survey data.
    template_content : str
        Markdown template string to render for each school.
    placeholders : list[str]
        List of variable names required by the template.
    output_dir : Path
        Directory where the generated markdown files are written.

    Returns
    -------
    int
        Number of successfully generated markdown files.

    Raises
    ------
    src.exceptions.DataValidationError
        If the CSV is missing required structural columns.
    OSError
        If output file writing fails due to a system error.

    Notes
    -----
    Output files are named ``{SchoolCode}.md``. All errors and skipped rows
    are logged for diagnostics.

    Examples
    --------
    >>> from pathlib import Path
    >>> n = process_csv_and_generate_markdowns(Path("schools.csv"), "# {SchoolCode}", ["SchoolCode"], Path("out_md"))
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

