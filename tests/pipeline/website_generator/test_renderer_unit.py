"""Unit tests for website renderer utilities. (unique module name)
"""

from pathlib import Path
import json

import pytest

from src.pipeline.website_generator import renderer as r
from src.config import FALLBACK_DESCRIPTION_HTML, ERROR_DESCRIPTION_HTML


def test_get_school_description_html_no_file(tmp_path: Path) -> None:
    assert r.get_school_description_html("X", tmp_path) == FALLBACK_DESCRIPTION_HTML


def test_get_school_description_html_success(monkeypatch, tmp_path: Path) -> None:
    md_file = tmp_path / "S.processed.md"
    md_file.write_text("# Hi")

    monkeypatch.setattr("markdown2.markdown", lambda txt, extras=None: "<p>Hi</p>")
    out = r.get_school_description_html("S", tmp_path)
    assert "Hi" in out


def test_get_school_description_html_markdown_exception(monkeypatch, tmp_path: Path) -> None:
    md_file = tmp_path / "S.processed.md"
    md_file.write_text("# Hi")

    def bad(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr("markdown2.markdown", bad)
    assert r.get_school_description_html("S", tmp_path) == ERROR_DESCRIPTION_HTML


def test_clean_html_output():
    raw = "<p>\n</p><p>&nbsp;</p><h1>Title</h1>\n<p><br/></p>\n<br/><br/>"
    cleaned = r.clean_html_output(raw)
    assert "Title" in cleaned


def test_write_html_and_no_data(tmp_path: Path) -> None:
    out = tmp_path / "out" / "index.html"
    r.write_html_output("<html></html>", out)
    assert out.exists()
    out2 = tmp_path / "out2" / "nodata.html"
    r.write_no_data_html(out2)
    assert out2.exists()


def test_generate_final_html(tmp_path: Path) -> None:
    tpl = tmp_path / "tpl.html"
    tpl.write_text("prefix{school_list_json}suffix")
    data = [{"code": "S", "name": "School"}]
    out = r.generate_final_html(data, tpl)
    assert "School" in out

