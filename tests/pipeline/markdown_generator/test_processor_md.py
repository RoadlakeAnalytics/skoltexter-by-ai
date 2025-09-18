"""Tests for the processor logic of the markdown generator (renamed to avoid name clash)."""

import src.program1_generate_markdowns as p1


def test_build_template_context_survey_branch():
    row = {"SchoolCode": "S1", "SurveyAnswerCategory_Math_2023/2024": "90"}
    placeholders = ["SurveyAnswerCategory_Math", "Other"]
    ctx = p1.build_template_context(row, placeholders)
    assert ctx["SurveyAnswerCategory_Math"] == "90"
