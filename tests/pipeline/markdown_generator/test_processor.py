"""Tests for the processor logic of the markdown generator.

Includes CSV processing, main entrypoint sanity checks and error paths.
"""

import sys
from pathlib import Path

import pytest

import src.program1_generate_markdowns as p1
from src.program1_generate_markdowns import (
    process_csv_and_generate_markdowns,
)


def test_build_template_context_survey_branch():
    row = {
        "SchoolCode": "S1",
        "SurveyAnswerCategory_Math_2023/2024": "90",
    }
    placeholders = ["SurveyAnswerCategory_Math", "Other"]
    ctx = p1.build_template_context(row, placeholders)
    assert ctx["SurveyAnswerCategory_Math"] == "90"


def test_process_csv_missing_schoolcode_skip(tmp_path: Path):
    csv_path = tmp_path / "s.csv"
    csv_path.write_text("SchoolCode;SchoolName\n;Name\n", encoding="utf-8")
    tpl = "# {SchoolName}\n{SchoolCode}"
    out = p1.process_csv_and_generate_markdowns(
        csv_path, tpl, ["SchoolName", "SchoolCode"], tmp_path / "out"
    )
    assert out == 0


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

