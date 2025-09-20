"""Extra tests for markdown processor helpers."""

from pathlib import Path

from src.pipeline.markdown_generator import processor as proc


def test_build_template_context_with_survey_answer(monkeypatch):
    """Survey answer placeholders are resolved using preferred year suffixes."""
    row = {"SchoolCode": "S1", "SurveyAnswerCategoryX_2023/2024": "42"}
    placeholders = ["SurveyAnswerCategoryX"]

    # Use the real helpers; validate returned context contains the value
    context = proc.build_template_context(row, placeholders)
    assert context["SchoolCode"] == "S1"
    assert context.get("SurveyAnswerCategoryX") == "42"


def test_process_csv_and_generate_markdowns_writes_files(monkeypatch, tmp_path: Path):
    """CSV rows should produce markdown files for valid SchoolCode entries."""
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("SchoolCode;Col\nS1;v1\nS2;v2\n")

    # Monkeypatch loader to read two rows
    monkeypatch.setattr(proc, "load_school_rows_from_csv", lambda p: ("ignored",))
    # Instead call the function with a fake loader via monkeypatching the loader
    from src.pipeline.markdown_generator.data_loader import (
        load_school_rows_from_csv as real_loader,
    )

    # Build a simple CSV and use the real loader implementation instead of the
    # monkeypatched placeholder above for this test's scope.
    monkeypatch.setattr(
        proc, "load_school_rows_from_csv", lambda p: real_loader(csv_path)
    )
    monkeypatch.setattr(proc, "render_template", lambda tpl, ctx: "--md--")

    outdir = tmp_path / "out"
    count = proc.process_csv_and_generate_markdowns(
        csv_path, "tpl", ["SchoolCode"], outdir
    )
    assert count == 2
    assert (outdir / "S1.md").exists()
    assert (outdir / "S2.md").exists()
