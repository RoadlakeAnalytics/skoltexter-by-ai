"""Markdown generator package.

Provides CSV loading, templating and processing helpers used by Program 1.
"""

from .data_loader import (
    determine_survey_year_for_report,
    get_survey_answer_value,
    get_value_from_row,
    load_school_rows_from_csv,
)
from .processor import build_template_context, process_csv_and_generate_markdowns
from .templating import (
    extract_placeholders_from_template,
    load_template_and_placeholders,
    render_template,
)

__all__ = [
    "get_value_from_row",
    "get_survey_answer_value",
    "determine_survey_year_for_report",
    "load_school_rows_from_csv",
    "process_csv_and_generate_markdowns",
    "build_template_context",
    "load_template_and_placeholders",
    "extract_placeholders_from_template",
    "render_template",
]
