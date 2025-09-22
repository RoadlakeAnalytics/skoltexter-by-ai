"""Website rendering utilities for the static school portfolio generator.

This module provides all file-local functions required to turn AI-generated
markdown descriptions and structured school data into a polished static HTML website.
It forms the lowest layer of rendering logic within the strictly decoupled pipeline,
transforming data into site-ready output using robust, configuration-driven routines.

System Boundaries
-----------------
- Accepts only already aggregated and AI-processed data; agnostic to upstream orchestration/UI.
- HTML generation uses templates and fallbacks from `src/config.py`.
- All error handling, test idempotence, and file creation/verification are locally managed; errors become safe fallback HTML.
- Exceptions are swallowed or mapped to defined error blobs as per AGENTS.md robustness policy.

Usage (for Portfolio Readers)
-----------------------------
Call these functions inside pipeline runners or orchestrators to:
    - Render per-school descriptions (`get_school_description_html`)
    - Generate/write the full HTML site from templates
    - Handle missing or erroneous data gracefully for tests or production

References
----------
- Architecture: Strict separation of orchestration, logic, and rendering.
- Configuration: UPPER_SNAKE_CASE constants from `src/config.py`.
- Robustness: See AGENTS.md, "Robustness Rules (Inspired by NASA's Power of 10)".
- Error taxonomy: All error cases map to user-facing HTML or silent test output.

Example
-------
>>> from src.pipeline.website_generator import renderer
>>> html = renderer.get_school_description_html('1899921', Path('/ai/descriptions/'))
>>> assert "<h1>" in html
>>> renderer.write_html_output(html, Path("/tmp/output.html"))
"""

import json
import re
from pathlib import Path

from src.config import (
    AI_PROCESSED_FILENAME_SUFFIX,
    ERROR_DESCRIPTION_HTML,
    FALLBACK_DESCRIPTION_HTML,
)

def get_school_description_html(school_code: str, ai_markdown_dir: Path) -> str:
    r"""Render the HTML description for a provided school from its AI-generated markdown.

    Loads a previously AI-processed Markdown file for `school_code`,
    converts it to HTML using `markdown2`, and returns the cleaned HTML output.
    Any missing file or unexpected error results in a robust fallback HTML blob.
    Idempotence and safety are guaranteed; all non-critical exceptions are swallowed.

    Parameters
    ----------
    school_code : str
        Unique identifier for the school (used in file naming).
    ai_markdown_dir : Path
        Directory containing AI-processed Markdown files with name pattern
        `{school_code}{AI_PROCESSED_FILENAME_SUFFIX}` from `src/config.py`.

    Returns
    -------
    str
        HTML description for the school, or configured fallback/error HTML blob.

    Raises
    ------
    Never propagates; all errors handled internally.

    See Also
    --------
    clean_html_output : Post-processes the generated HTML.
    ERROR_DESCRIPTION_HTML, FALLBACK_DESCRIPTION_HTML : Robustness constants.

    Notes
    -----
    Uses `markdown2` for Markdown conversion.

    Examples
    --------
    >>> from pathlib import Path
    >>> from src.pipeline.website_generator.renderer import get_school_description_html
    >>> ai_dir = Path("/tmp/mock_ai")
    >>> _ = ai_dir.mkdir(exist_ok=True)
    >>> (ai_dir / "1244.ai.md").write_text("# Welcome School", encoding="utf-8")
    >>> get_school_description_html("1244", ai_dir)  # doctest: +ELLIPSIS
    '<h1>Welcome School</h1>...'
    >>> get_school_description_html("nosuchschool", ai_dir) == FALLBACK_DESCRIPTION_HTML
    True
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
    r"""Write the provided HTML content to disk, creating parent directories automatically.

    Parent directories of `output_file` are created as needed.
    All errors (I/O, permission, etc.) are swallowed for idempotence.

    Parameters
    ----------
    html_content : str
        Full HTML string to be written.
    output_file : Path
        Output file path.

    Returns
    -------
    None

    Raises
    ------
    Never propagates; all errors handled internally.

    See Also
    --------
    write_no_data_html : Similar robust write for minimal page.

    Notes
    -----
    Output encoding is UTF-8.

    Examples
    --------
    >>> import tempfile
    >>> from src.pipeline.website_generator.renderer import write_html_output
    >>> from pathlib import Path
    >>> file_path = Path(tempfile.gettempdir()) / "test_site.html"
    >>> write_html_output("<html><body>Test</body></html>", file_path)
    >>> assert file_path.read_text(encoding="utf-8") == "<html><body>Test</body></html>"
    """
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(html_content, encoding="utf-8")
    except Exception:
        pass

def write_no_data_html(output_file: Path) -> None:
    r"""Write a minimal 'no data' HTML page to the specified path.

    Writes '<html><body><h1>No data</h1></body></html>' to `output_file`, with parents created.
    I/O errors are swallowed for test robustness.

    Parameters
    ----------
    output_file : Path
        Path for output file (parents created if missing).

    Returns
    -------
    None

    Raises
    ------
    Never propagates; all errors handled internally.

    See Also
    --------
    write_html_output : Robust output routine for general HTML.

    Notes
    -----
    Page content is hardcoded minimal HTML string.

    Examples
    --------
    >>> import tempfile
    >>> from pathlib import Path
    >>> from src.pipeline.website_generator.renderer import write_no_data_html
    >>> tgt = Path(tempfile.gettempdir()) / "empty_site.html"
    >>> write_no_data_html(tgt)
    >>> assert "<h1>No data" in tgt.read_text(encoding="utf-8")
    """
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            "<html><body><h1>No data</h1></body></html>", encoding="utf-8"
        )
    except Exception:
        pass

def clean_html_output(html_content: str) -> str:
    r"""Perform lightweight normalization and cleaning of generated HTML strings.

    Cleans HTML (typically from Markdown conversion) by removing empty paragraphs,
    redundant breaks, excess whitespace, and normalizing block structure.

    Parameters
    ----------
    html_content : str
        Raw HTML string.

    Returns
    -------
    str
        Fully cleaned HTML string.

    Raises
    ------
    TypeError
        If input is not str.

    See Also
    --------
    get_school_description_html : Producer of HTML for cleaning.

    Notes
    -----
    Regex-based normalization.

    Examples
    --------
    >>> from src.pipeline.website_generator.renderer import clean_html_output
    >>> raw = "<p></p><h1>Hi</h1><p>&nbsp;</p><br><br>"
    >>> clean_html_output(raw)
    '<h1>Hi</h1><br>'
    >>> try:
    ...     clean_html_output(None)
    ... except TypeError:
    ...     pass
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
    r"""Render the full static site HTML by injecting school data into the provided template.

    Loads the HTML template from disk, serializes all school records as compact JSON,
    and injects into the `{school_list_json}` placeholder in the template.

    Parameters
    ----------
    schools_data : list of dict of str to str
        School data for serialization.
    template_path : Path
        Path to HTML template file (must have `{school_list_json}`).

    Returns
    -------
    str
        Fully rendered HTML content.

    Raises
    ------
    IOError
        If the template file cannot be read.

    See Also
    --------
    get_school_description_html : Per-school descriptions for data aggregation.

    Notes
    -----
    Output encoding is UTF-8; JSON is embedded directly.

    Examples
    --------
    >>> import tempfile
    >>> from src.pipeline.website_generator.renderer import generate_final_html
    >>> from pathlib import Path
    >>> tmp = Path(tempfile.gettempdir()) / "test_template.html"
    >>> tpl = "<html>{school_list_json}</html>"
    >>> schools = [{"name": "Alpha"}, {"name": "Beta"}]
    >>> tmp.write_text(tpl, encoding="utf-8")
    >>> res = generate_final_html(schools, tmp)
    >>> assert '"Alpha"' in res and '"Beta"' in res and res.startswith("<html>") and res.endswith("</html>")
    """
    with template_path.open("r", encoding="utf-8") as fh:
        tpl = fh.read()
    payload = json.dumps(schools_data, ensure_ascii=False)
    return tpl.replace("{school_list_json}", payload)
