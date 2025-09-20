"""Extra tests for website renderer utilities."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.config import ERROR_DESCRIPTION_HTML, FALLBACK_DESCRIPTION_HTML
from src.pipeline.website_generator import renderer as r


def test_get_school_description_html_missing_file(tmp_path: Path) -> None:
    """Return fallback HTML when the processed markdown does not exist."""
    out = r.get_school_description_html("missing", tmp_path)
    assert out == FALLBACK_DESCRIPTION_HTML


def test_get_school_description_html_markdown2_error(
    tmp_path: Path, monkeypatch
) -> None:
    """If markdown2 raises, return the error HTML blob."""
    p = tmp_path / "S1.processed.md"
    p.write_text("# Title\nContent")

    # Install a fake markdown2 that raises during conversion
    fake_mod = SimpleNamespace(
        markdown=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    monkeypatch.setitem(sys.modules, "markdown2", fake_mod)
    out = r.get_school_description_html("S1", tmp_path)
    assert out == ERROR_DESCRIPTION_HTML


def test_clean_html_output_raises_on_non_string() -> None:
    """Non-string inputs must raise a TypeError for safety."""
    with pytest.raises(TypeError):
        r.clean_html_output(123)  # type: ignore[arg-type]


def test_clean_html_output_removes_empty_paragraphs_and_br() -> None:
    """Verify regex-driven cleanup rules produce a compact HTML string."""
    src = "<p> </p>\n<p>&nbsp;</p>\n<p><br/></p>\n<h1>Hi</h1>\n<p></p>\n<br>\n<br>\n\nMore"
    out = r.clean_html_output(src)
    assert "<p> </p>" not in out
    assert "&nbsp;" not in out
    assert "<p><br" not in out
    assert out.startswith("<h1>Hi</h1>")


def test_generate_final_html_inserts_json(tmp_path: Path) -> None:
    """The template placeholder must be replaced with JSON-serialized data."""
    tpl = tmp_path / "tpl.html"
    tpl.write_text("PRE{school_list_json}POST", encoding="utf-8")
    data = [{"a": 1}, {"b": 2}]
    out = r.generate_final_html(data, tpl)
    assert "PRE" in out and "POST" in out
    assert json.dumps(data, ensure_ascii=False) in out
