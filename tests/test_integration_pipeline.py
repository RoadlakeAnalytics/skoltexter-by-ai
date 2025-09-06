"""Integration test: minimal end-to-end flow without real API calls.

Generates markdown from CSV (Program 1), simulates AI output, then builds
final HTML (Program 3). Ensures the combined output includes expected names.
"""

import json
from pathlib import Path

import pandas as pd

from src.program1_generate_markdowns import (
    load_template_and_placeholders,
    process_csv_and_generate_markdowns,
)
from src.program3_generate_website import generate_html_content, load_school_data


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


def test_end_to_end_without_api(tmp_path: Path):
    """Run a minimal end-to-end flow without real API calls.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory provided by pytest.

    Returns
    -------
    None
        Asserts that generated HTML contains expected school names.
    """
    # Arrange a small CSV with two schools
    csv_path = tmp_path / "schools.csv"
    df = pd.DataFrame(
        [
            {"SchoolCode": "A100", "SchoolName": "Alpha"},
            {"SchoolCode": "B200", "SchoolName": ""},
        ]
    )
    df.to_csv(csv_path, sep=";", index=False)

    # Minimal template used by program1
    template_path = tmp_path / "template.md"
    template_text = "# {SchoolName}\nCode: {SchoolCode}\n"
    write_file(template_path, template_text)

    # Generate markdown files (program1)
    template_content, placeholders = load_template_and_placeholders(template_path)
    gen_dir = tmp_path / "generated"
    count = process_csv_and_generate_markdowns(
        csv_path, template_content, placeholders, gen_dir
    )
    assert count == 2

    # Simulate program2 output by writing expected AI markdown files
    ai_dir = tmp_path / "ai_processed_markdown"
    write_file(ai_dir / "A100_ai_description.md", "**AI**: Alpha is great!")
    write_file(ai_dir / "B200_ai_description.md", "**AI**: B200 fallback text.")

    # Build website content (program3)
    schools = load_school_data(csv_path, ai_dir)
    assert len(schools) == 2
    html = generate_html_content(json.dumps(schools, ensure_ascii=False))
    # Smoke assertions that expected names appear in final HTML
    assert "Alpha" in html
    assert "B200" in html or "fallback" in html
