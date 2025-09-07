"""Tests for Program 3: Website generation.

Validates CSV reading and error paths, record deduplication and fallback naming,
markdown-to-HTML conversion and cleanup, HTML writing, fallback HTML, and
end-to-end CLI flow. NumPy-style docstrings for consistency.
"""

import sys
from pathlib import Path

import pandas as pd

# ---- Extra paths consolidated from test_program3_extra_paths.py ----
import pytest

import src.program3_generate_website as p3
from src.program3_generate_website import (
    clean_html_output,
    deduplicate_and_format_school_records,
    load_school_data,
    read_school_csv,
    write_no_data_html,
)


def test_setup_logging_filehandler_error(monkeypatch):
    class BadFH:
        def __init__(self, *a, **k):
            raise RuntimeError("fh error")

    monkeypatch.setattr(p3.logging, "FileHandler", BadFH)
    p3.setup_logging("INFO", enable_file=True)


def test_read_school_csv_bad_columns(tmp_path: Path):
    # Create CSV with unexpected columns -> ValueError due to usecols
    csvp = tmp_path / "bad.csv"
    csvp.write_text("A;B\n1;2\n", encoding="utf-8")
    df = p3.read_school_csv(csvp)
    # When pandas raises ValueError, function returns empty DataFrame
    assert df.empty


def test_read_school_csv_generic_exception(monkeypatch, tmp_path: Path):
    def bad_read_csv(*a, **k):
        raise TypeError("boom")

    monkeypatch.setattr(p3.pd, "read_csv", bad_read_csv)
    df = p3.read_school_csv(tmp_path / "x.csv")
    assert df.empty


def test_deduplicate_and_format_school_records_empty_df():
    df = pd.DataFrame(columns=["SchoolCode", "SchoolName"])
    out = p3.deduplicate_and_format_school_records(df)
    assert out == []


def test_clean_html_output_type_error():
    with pytest.raises(TypeError):
        p3.clean_html_output(123)  # type: ignore[arg-type]


def test_write_html_output_errors(monkeypatch, tmp_path: Path):
    out = tmp_path / "site" / "index.html"

    def bad_write_text(self, content, encoding="utf-8"):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_text", bad_write_text)
    p3.write_html_output("<html></html>", out)

    def bad_write_text2(self, content, encoding="utf-8"):
        raise RuntimeError("boom")

    monkeypatch.setattr(Path, "write_text", bad_write_text2)
    p3.write_html_output("<html></html>", out)


def test_write_no_data_html_oserror(monkeypatch, tmp_path: Path):
    out = tmp_path / "index.html"

    def bad_write_text(self, content, encoding="utf-8"):
        raise OSError("no")

    monkeypatch.setattr(Path, "write_text", bad_write_text)
    p3.write_no_data_html(out)


def test_get_school_description_html_not_found(tmp_path: Path):
    ai_dir = tmp_path / "ai"
    ai_dir.mkdir()
    html = p3.get_school_description_html("S1", ai_dir)
    assert isinstance(html, str)


def test_clean_html_output_removes_empty_and_compacts():
    """Verify HTML cleanup removes empty tags and reduces breaks.

    Returns
    -------
    None
        Asserts the cleaned HTML string matches expectations.
    """
    raw_html = "<p>Title</p><p>  </p><p><br/></p><div>Content</div><br><br>"
    assert clean_html_output(raw_html) == "<p>Title</p><div>Content</div><br>"
    raw_html2 = "<h2>Header</h2><br><br><p>&nbsp;</p><p>Text</p>"
    out2 = clean_html_output(raw_html2)
    assert "&nbsp;" not in out2 and "<br><br>" not in out2


def test_deduplicate_and_format_school_records_basic():
    """Confirm deduplication and fallback naming on school records.

    Returns
    -------
    None
        Asserts output ordering and fallback application.
    """
    df = pd.DataFrame(
        [
            {"SchoolCode": "A", "SchoolName": "Alpha"},
            {"SchoolCode": "A", "SchoolName": "Alpha Again"},
            {"SchoolCode": "B", "SchoolName": ""},
            {"SchoolCode": "", "SchoolName": "NoCode"},
        ]
    )
    out = deduplicate_and_format_school_records(df)
    assert out[0] == {"id": "A", "name": "Alpha"}
    assert out[1]["id"] == "B"


def test_write_no_data_html_creates_file(tmp_path: Path):
    """Write fallback HTML when no data exists and verify content.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory provided by pytest.
    """
    out = tmp_path / "index.html"
    write_no_data_html(out)
    assert out.exists()
    html = out.read_text(encoding="utf-8").lower()
    assert "no school data" in html or "no data" in html


def test_program3_main_generates_html(tmp_path: Path, monkeypatch):
    """Run program3 main end-to-end in tmp and verify HTML includes data."""
    csv_path = tmp_path / "schools.csv"
    df = pd.DataFrame(
        [
            {"SchoolCode": "C01", "SchoolName": "Charlie"},
        ]
    )
    df.to_csv(csv_path, sep=";", index=False)
    ai_dir = tmp_path / "ai"
    ai_dir.mkdir()
    (ai_dir / "C01_ai_description.md").write_text("Hello from AI", encoding="utf-8")
    out_file = tmp_path / "site.html"
    monkeypatch.setenv("DISABLE_FILE_LOGS", "1")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "program3_generate_website.py",
            "--csv",
            str(csv_path),
            "--markdown_dir",
            str(ai_dir),
            "--output",
            str(out_file),
        ],
    )
    p3.main()
    assert out_file.exists()
    html = out_file.read_text(encoding="utf-8")
    assert "Charlie" in html and "Hello from AI" in html


def test_read_school_csv_missing_file(tmp_path: Path):
    """Reading a missing CSV yields an empty DataFrame and logs error."""
    df = read_school_csv(tmp_path / "no.csv")
    assert df.empty


def test_load_school_data_empty(tmp_path: Path):
    """Load school data returns empty list for empty CSV."""
    csv_path = tmp_path / "x.csv"
    csv_path.write_text("SchoolCode;SchoolName\n", encoding="utf-8")
    out = load_school_data(csv_path, tmp_path)
    assert out == []


def test_program3_main_no_data(tmp_path: Path, monkeypatch):
    """Run main with empty CSV -> expect fallback HTML is written."""
    csv_path = tmp_path / "schools.csv"
    csv_path.write_text("SchoolCode;SchoolName\n", encoding="utf-8")
    out_file = tmp_path / "site.html"
    monkeypatch.setenv("DISABLE_FILE_LOGS", "1")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "program3_generate_website.py",
            "--csv",
            str(csv_path),
            "--markdown_dir",
            str(tmp_path / "ai"),
            "--output",
            str(out_file),
        ],
    )
    p3.main()
    assert out_file.exists()
    html = out_file.read_text(encoding="utf-8").lower()
    assert "no data" in html or "no school data" in html


def test_get_school_description_html_markdown_error(monkeypatch, tmp_path: Path):
    from src import program3_generate_website as mod

    ai_dir = tmp_path / "ai"
    ai_dir.mkdir()
    (ai_dir / "S1_ai_description.md").write_text("X", encoding="utf-8")
    monkeypatch.setattr(
        mod.markdown2,
        "markdown",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("md fail")),
    )
    html = mod.get_school_description_html("S1", ai_dir)
    assert "Error" in html or "error" in html
