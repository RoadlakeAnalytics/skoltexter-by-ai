"""Processing logic for markdown generation."""

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
    """Build a mapping of template placeholders to values for a CSV row.

    Parameters
    ----------
    row : dict[str, str]
        CSV row mapping column names to values.
    template_placeholders : list[str]
        Placeholders present in the template that need values.

    Returns
    -------
    dict[str, str]
        Mapping from placeholder names to string values.
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
    """Process the CSV file and write one markdown file per school.

    Parameters
    ----------
    csv_path : Path
        Path to the input CSV file.
    template_content : str
        The text template used to render each school's markdown.
    placeholders : list[str]
        Placeholders to populate in the template.
    output_dir : Path
        Directory where generated markdown files are written.

    Returns
    -------
    int
        Number of markdown files successfully generated.
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
