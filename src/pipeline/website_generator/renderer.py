"""Rendering utilities for the static website."""

import json
import re
from pathlib import Path

from src.config import (
    AI_PROCESSED_FILENAME_SUFFIX,
    ERROR_DESCRIPTION_HTML,
    FALLBACK_DESCRIPTION_HTML,
)


def get_school_description_html(school_code: str, ai_markdown_dir: Path) -> str:
    """Return the HTML description for a school from its processed markdown.

    Parameters
    ----------
    school_code : str
        Identifier for the school.
    ai_markdown_dir : Path
        Directory containing processed AI markdown files.

    Returns
    -------
    str
        HTML content for the school's description or a fallback/error blob.
    """
    markdown_file_path = (
        ai_markdown_dir / f"{school_code}{AI_PROCESSED_FILENAME_SUFFIX}"
    )
    if not markdown_file_path.exists():
        return FALLBACK_DESCRIPTION_HTML
    try:
        import markdown2

        markdown_text = markdown_file_path.read_text(encoding="utf-8")
        description_html = markdown2.markdown(
            markdown_text, extras=["tables", "fenced-code-blocks"]
        )
        return clean_html_output(description_html)
    except Exception:
        return ERROR_DESCRIPTION_HTML


def write_html_output(html_content: str, output_file: Path) -> None:
    """Write the final HTML content to disk, creating parent directories.

    Any write errors are swallowed to keep rendering idempotent for tests.
    """
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(html_content, encoding="utf-8")
    except Exception:
        pass


def write_no_data_html(output_file: Path) -> None:
    """Write a minimal 'no data' HTML page to the given path."""
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            "<html><body><h1>No data</h1></body></html>", encoding="utf-8"
        )
    except Exception:
        pass


def clean_html_output(html_content: str) -> str:
    """Perform lightweight post-processing on generated HTML.

    Parameters
    ----------
    html_content : str
        Raw HTML generated from markdown.

    Returns
    -------
    str
        Cleaned HTML string.
    """
    if not isinstance(html_content, str):
        raise TypeError("Input must be a string.")
    html_content = re.sub(r"<p>\s*</p>", "", html_content)
    html_content = re.sub(r"<p>&nbsp;</p>", "", html_content)
    html_content = re.sub(r"<p><br\s*/?>\s*</p>", "", html_content)
    html_content = re.sub(
        r"(<h[1-6][^>]*>.*?</h[1-6]>)\s*<p>\s*</p>", r"\1", html_content
    )
    html_content = re.sub(r"(<br\s*/?>\s*){2,}", "<br>", html_content)
    html_content = re.sub(r"\n\s*\n\s*\n+", "\n\n", html_content)
    html_content = re.sub(r">\s+<", "><", html_content)
    return html_content.strip()


def generate_final_html(schools_data: list[dict[str, str]], template_path: Path) -> str:
    """Render the final HTML site by injecting school data as JSON.

    Parameters
    ----------
    schools_data : list[dict[str, str]]
        List of school dictionaries to serialize into the page.
    template_path : Path
        Path to the HTML template containing a ``{school_list_json}`` placeholder.

    Returns
    -------
    str
        Final HTML content with the embedded school data.
    """
    with template_path.open("r", encoding="utf-8") as fh:
        tpl = fh.read()
    payload = json.dumps(schools_data, ensure_ascii=False)
    return tpl.replace("{school_list_json}", payload)
