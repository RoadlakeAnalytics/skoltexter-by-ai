"""Templating tests for the markdown generator.
"""

import pytest

from src.pipeline.markdown_generator.templating import (
    extract_placeholders_from_template,
    render_template,
    load_template_and_placeholders,
)


def test_extract_placeholders_from_template_basic():
    template = "Hello {SchoolName}! Code: {SchoolCode}. {SurveyAnswerCategory_Math}"
    out = extract_placeholders_from_template(template)
    assert out == ["SchoolCode", "SchoolName", "SurveyAnswerCategory_Math"]

