"""Tests for HTML rendering and file output in program3_generate_website."""

import pytest

from src.pipeline.website_generator import renderer as p3


def test_clean_html_output_type_error():
    """Test Clean html output type error."""
    with pytest.raises(TypeError):
        p3.clean_html_output(123)  # type: ignore[arg-type]
