"""Tests for Program 1: Markdown generation from CSV.

Covers placeholder extraction, rendering rules, CSV parsing, context
building, file-writing error handling, logging configuration, and the CLI
``main`` path. NumPy-style docstrings are used for consistency.
"""

# ---- Extra paths consolidated from test_program1_extra_paths.py ----
import logging
import sys
from pathlib import Path

import pytest

import src.program1_generate_markdowns as p1
from src.program1_generate_markdowns import (
    determine_survey_year_for_report,
    extract_placeholders_from_template,
    get_survey_answer_value,
    get_value_from_row,
    load_template_and_placeholders,
    process_csv_and_generate_markdowns,
    render_template,
)


def test_configure_logging_filehandler_error(monkeypatch):
    class BadFH:
        def __init__(self, *a, **k):
            raise RuntimeError("fh error")

    monkeypatch.setattr(p1.logging, "FileHandler", BadFH)
    p1.configure_logging("INFO", enable_file=True)


def test_build_template_context_survey_branch():
    row = {
        "SchoolCode": "S1",
        "SurveyAnswerCategory_Math_2023/2024": "90",
    }
    placeholders = ["SurveyAnswerCategory_Math", "Other"]
    ctx = p1.build_template_context(row, placeholders)
    assert ctx["SurveyAnswerCategory_Math"] == "90"


def test_get_survey_answer_value_fallback():
    row = {}
    assert (
        p1.get_survey_answer_value(row, "SurveyAnswerCategory_None")
        == p1.MISSING_DATA_PLACEHOLDER
    )


def test_process_csv_missing_schoolcode_skip(tmp_path: Path):
    csv_path = tmp_path / "s.csv"
    csv_path.write_text("SchoolCode;SchoolName\n;Name\n", encoding="utf-8")
    tpl = "# {SchoolName}\n{SchoolCode}"
    out = p1.process_csv_and_generate_markdowns(
        csv_path, tpl, ["SchoolName", "SchoolCode"], tmp_path / "out"
    )
    assert out == 0


def test_flush_and_close_log_handlers_exceptions(monkeypatch):
    class BadHandler(logging.Handler):
        def flush(self):
            raise RuntimeError("flush bad")

        def close(self):
            raise RuntimeError("close bad")

    h = BadHandler()
    logging.root.addHandler(h)
    # Should not raise
    p1.flush_and_close_log_handlers()
    # Clean up the handler to avoid side effects on other tests
    logging.root.removeHandler(h)


def test_main_generic_exception(monkeypatch, tmp_path: Path):
    class Bad:
        def __call__(self, *a, **k):
            raise RuntimeError("boom")

    monkeypatch.setattr(p1, "load_template_and_placeholders", Bad())
    monkeypatch.setenv("DISABLE_FILE_LOGS", "1")
    # Prepare args so main proceeds to the try block
    csv_path = tmp_path / "schools.csv"
    csv_path.write_text("SchoolCode;SchoolName\nA;A\n", encoding="utf-8")
    tpl_path = tmp_path / "tpl.md"
    tpl_path.write_text("{SchoolName}", encoding="utf-8")
    out_dir = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "program1_generate_markdowns.py",
            "--csv-path",
            str(csv_path),
            "--template-path",
            str(tpl_path),
            "--output-dir",
            str(out_dir),
        ],
    )
    p1.main()


def test_extract_placeholders_from_template_basic():
    """Validate placeholder extraction from a simple template.

    Returns
    -------
    None
        Asserts that all placeholders are discovered in sorted order.
    """
    template = "Hello {SchoolName}! Code: {SchoolCode}. {SurveyAnswerCategory_Math}"
    out = extract_placeholders_from_template(template)
    assert out == ["SchoolCode", "SchoolName", "SurveyAnswerCategory_Math"]


def test_render_template_formats_numbers_and_placeholders():
    """Ensure rendering formats numeric strings and fills missing values.

    Returns
    -------
    None
        Asserts formatted output and presence of placeholders when missing.
    """
    tpl = "Name: {SchoolName}, Code: {SchoolCode}, Score: {Score}"
    ctx = {"SchoolName": "Alpha", "SchoolCode": "A-01", "Score": "10.0"}
    assert render_template(tpl, ctx) == "Name: Alpha, Code: A-01, Score: 10"
    ctx2 = {"SchoolName": "Beta"}
    out = render_template(tpl, ctx2)
    assert "Beta" in out and "[Data Saknas]" in out
    # Negative integer-like formatting
    tpl2 = "Score: {Score}"
    ctx3 = {"Score": "-5.0"}
    assert render_template(tpl2, ctx3) == "Score: -5"

    # Duplicate placeholders should not break extraction/render
    tpl_dup = "{SchoolCode}-{SchoolCode}"
    assert render_template(tpl_dup, {"SchoolCode": "X"}) == "X-X"


def test_get_value_from_row_and_survey_helpers():
    """Check CSV value cleanup and survey helper preference order.

    Returns
    -------
    None
        Asserts trimming, placeholder fallback, and year selection logic.
    """
    row = {"SchoolCode": "  123  ", "X": "N/A"}
    assert get_value_from_row(row, "SchoolCode") == "123"
    assert get_value_from_row(row, "X") == "[Data Saknas]"
    assert get_value_from_row(row, "Missing") == "[Data Saknas]"

    # Survey value: prefer latest non-empty according to config order
    row2 = {
        "SurveyAnswerCategory_Read_2023/2024": "",
        "SurveyAnswerCategory_Read_2022/2023": "72",
    }
    assert get_survey_answer_value(row2, "SurveyAnswerCategory_Read") == "72"

    placeholders = ["SurveyAnswerCategory_Read", "SchoolCode"]
    row3 = {
        "SurveyAnswerCategory_Read_2023/2024": "85",
        "SurveyAnswerCategory_Read_2022/2023": "70",
    }
    assert determine_survey_year_for_report(row3, placeholders) == "2023/2024"


def test_determine_survey_year_for_report_all_missing():
    """When all survey values are missing, return the placeholder marker.

    This exercises the false branch of the inner condition to achieve full
    branch coverage in ``determine_survey_year_for_report``.
    """
    placeholders = ["SurveyAnswerCategory_Science", "SchoolCode"]
    row = {
        "SurveyAnswerCategory_Science_2023/2024": "",
        "SurveyAnswerCategory_Science_2022/2023": "",
    }
    out = determine_survey_year_for_report(row, placeholders)
    assert out == p1.MISSING_DATA_PLACEHOLDER


def write_file(path: Path, text: str) -> None:
    """Write helper that ensures parent directory exists.

    Parameters
    ----------
    path : Path
        Target file path to write.
    text : str
        File content to write in UTF-8.

    Returns
    -------
    None
        Creates parent directories and writes content.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_load_template_without_placeholders_raises(tmp_path: Path):
    """Ensure loader raises for templates without placeholders.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
        Asserts ValueError is raised.
    """
    tpl = tmp_path / "tpl.md"
    tpl.write_text("No placeholders here", encoding="utf-8")
    with pytest.raises(ValueError):
        load_template_and_placeholders(tpl)


def test_program1_main_happy_path(tmp_path: Path, monkeypatch):
    """Run program1 main end-to-end with temp CSV/template.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory provided by pytest.
    monkeypatch : MonkeyPatch
        Fixture to patch argv and disable file logs.

    Returns
    -------
    None
        Asserts output markdown file content.
    """
    # Prepare CSV and template and output dir
    csv_path = tmp_path / "schools.csv"
    csv_path.write_text("SchoolCode;SchoolName\nA01;Alpha\n", encoding="utf-8")
    template_path = tmp_path / "tpl.md"
    template_path.write_text("# {SchoolName}\nCode: {SchoolCode}\n", encoding="utf-8")
    out_dir = tmp_path / "out"

    monkeypatch.setenv("DISABLE_FILE_LOGS", "1")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "program1_generate_markdowns.py",
            "--csv-path",
            str(csv_path),
            "--template-path",
            str(template_path),
            "--output-dir",
            str(out_dir),
            "--log-level",
            "INFO",
        ],
    )

    p1.main()
    out_file = out_dir / "A01.md"
    assert out_file.exists()
    assert "Alpha" in out_file.read_text(encoding="utf-8")


def test_process_csv_empty_returns_zero(tmp_path: Path):
    """Empty CSV (no header) yields zero processed files.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory provided by pytest.
    """
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("", encoding="utf-8")
    tpl_content = "# {SchoolName}\nCode: {SchoolCode}\n"
    placeholders = ["SchoolName", "SchoolCode"]
    out = process_csv_and_generate_markdowns(
        csv_path, tpl_content, placeholders, tmp_path / "out"
    )
    assert out == 0


def test_program1_main_missing_files(monkeypatch, tmp_path: Path, capsys):
    """Invoke main with missing CSV and template to cover exceptions."""
    missing_csv = tmp_path / "no.csv"
    missing_tpl = tmp_path / "no.md"
    out_dir = tmp_path / "out"
    monkeypatch.setenv("DISABLE_FILE_LOGS", "1")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "program1_generate_markdowns.py",
            "--csv-path",
            str(missing_csv),
            "--template-path",
            str(missing_tpl),
            "--output-dir",
            str(out_dir),
        ],
    )
    p1.main()
    capsys.readouterr()  # ensure no crash


def test_process_csv_write_error(tmp_path: Path, monkeypatch):
    """Simulate write error for one output file to cover exception path."""
    csv_path = tmp_path / "schools.csv"
    csv_path.write_text("SchoolCode;SchoolName\nX;Xname\n", encoding="utf-8")
    tpl_content = "# {SchoolName}\nCode: {SchoolCode}\n"
    placeholders = ["SchoolName", "SchoolCode"]
    out_dir = tmp_path / "out"
    bad_path = out_dir / "X.md"
    orig_open = Path.open

    def bad_open(self, mode="r", *a, **k):
        if self == bad_path and "w" in mode:
            raise OSError("disk full")
        return orig_open(self, mode, *a, **k)

    monkeypatch.setattr(Path, "open", bad_open)
    count = process_csv_and_generate_markdowns(
        csv_path, tpl_content, placeholders, out_dir
    )
    assert count == 0  # write failed; handled internally and not counted
