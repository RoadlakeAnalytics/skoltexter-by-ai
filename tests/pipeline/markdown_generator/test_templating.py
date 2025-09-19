"""Templating tests for the markdown generator."""

from src.pipeline.markdown_generator.templating import (
    extract_placeholders_from_template,
)


def test_extract_placeholders_from_template_basic():
    """Test Extract placeholders from template basic."""
    template = "Hello {SchoolName}! Code: {SchoolCode}. {SurveyAnswerCategory_Math}"
    out = extract_placeholders_from_template(template)
    assert out == ["SchoolCode", "SchoolName", "SurveyAnswerCategory_Math"]
