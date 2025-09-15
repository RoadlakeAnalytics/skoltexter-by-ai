"""Tests for data loader helpers in the program1 markdown generator.
"""

from src.pipeline.markdown_generator import data_loader as p1
from src.pipeline.markdown_generator.data_loader import (
    get_value_from_row,
    get_survey_answer_value,
    determine_survey_year_for_report,
)


def test_get_value_from_row_and_survey_helpers():
    row = {"SchoolCode": "  123  ", "X": "N/A"}
    assert get_value_from_row(row, "SchoolCode") == "123"
    assert get_value_from_row(row, "X") == "[Data Saknas]"
    assert get_value_from_row(row, "Missing") == "[Data Saknas]"

