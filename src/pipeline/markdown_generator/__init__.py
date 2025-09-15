"""Markdown generator package.

Provides CSV loading, templating and processing helpers used by Program 1.
"""

from .data_loader import (
    get_value_from_row,
    get_survey_answer_value,
    determine_survey_year_for_report,
    load_school_rows_from_csv,
)
from .processor import process_csv_and_generate_markdowns, build_template_context
from .templating import load_template_and_placeholders, extract_placeholders_from_template, render_template

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

