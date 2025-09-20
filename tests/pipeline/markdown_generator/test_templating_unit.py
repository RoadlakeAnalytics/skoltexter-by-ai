"""Unit tests for the markdown templating utilities.

These tests cover placeholder extraction, rendering semantics (including
numeric formatting) and the helper that loads templates and validates
that placeholders are present.
"""

from pathlib import Path

import pytest

from src.pipeline.markdown_generator import templating as tpl
from src.config import MISSING_DATA_PLACEHOLDER


def test_extract_placeholders_and_render_numeric_and_missing() -> None:
    """Extract placeholders and render replacement values correctly.

    Ensures that duplicate placeholders are deduplicated, numeric strings
    like "10.0" are rendered as "10", and missing keys use the global
    missing-data placeholder.
    """
    content = "Hello {name}, value: {val}, duplicate: {name}, nested {a_b/c}"
    placeholders = tpl.extract_placeholders_from_template(content)
    assert set(placeholders) == {"name", "val", "a_b/c"}

    rendered = tpl.render_template("X {val} Y {missing}", {"val": "10.0"})
    assert "10" in rendered
    assert MISSING_DATA_PLACEHOLDER in rendered


def test_load_template_and_placeholders_raises(tmp_path: Path) -> None:
    """Loading a template without placeholders raises ValueError."""
    p = tmp_path / "tpl.md"
    p.write_text("No placeholders here")
    with pytest.raises(ValueError):
        tpl.load_template_and_placeholders(p)

