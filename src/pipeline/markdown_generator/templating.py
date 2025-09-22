"""Templating utilities for Markdown-driven website generation.

This module provides a robust, stateless templating API for the School Data Pipeline project.
Its sole responsibility is handling template file loading, placeholder extraction, and
context-driven rendering, enabling clean transformation of CSV-driven data into human-friendly
Markdown blocks. All code is rigorously decoupled—no pipeline, orchestration, or side-effect logic
lives here. It is built to be usable from tests, CLI scripts, and orchestrators alike.

Boundaries
----------
- Does not write to disk or interact with network/IO outside template file reads.
- Only string and file Path handling; does not interpret Markdown or HTML.
- No external side effects; deterministic given inputs.
- All configuration (e.g., missing data placeholder) is injected from `src/config.py`.

References
----------
- See `AGENTS.md`, "Templating for Separation of Concerns".
- Template files: `data/templates/school_description_template.md`, etc.
- Used by: `src/pipeline/markdown_generator/runner.py, processor.py`.

Portfolio Usage
---------------
Example usage in a pipeline step:

>>> from src.pipeline.markdown_generator.templating import (
...     load_template, extract_placeholders_from_template, render_template
... )
>>> template = load_template(Path("data/templates/school_description_template.md"))
>>> placeholders = extract_placeholders_from_template(template)
>>> output = render_template(template, {"Name": "Sundby School", "Location": "Stockholm"})
>>> assert isinstance(output, str)
"""

import re
from pathlib import Path

from src.config import MISSING_DATA_PLACEHOLDER


def load_template(path: Path) -> str:
    r"""Read the contents of a template file as a string.

    Loads a Markdown or text template from disk to memory. Used as the first step in
    all site and prompt templating. This function is strictly responsible for reading
    the file and does not perform validation or placeholder extraction.

    Parameters
    ----------
    path : Path
        Path to the template file to be loaded.

    Returns
    -------
    str
        Contents of the template file as a string.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    OSError
        If the file cannot be read due to permissions or disk errors.

    Examples
    --------
    >>> from pathlib import Path
    >>> from src.pipeline.markdown_generator.templating import load_template
    >>> path = Path("data/templates/school_description_template.md")
    >>> content = load_template(path)
    >>> assert isinstance(content, str) and "{Name}" in content
    """

    Parameters
    ----------
    path : Path
        Path to the template file.

    Returns
    -------
    str
        Template content.
    """
    with path.open("r", encoding="utf-8") as fh:
        return fh.read()


def extract_placeholders_from_template(content: str) -> list[str]:
    """Return a sorted list of unique placeholders found in the template.

    Placeholders are tokens of the form ``{Name}`` where the name can
    contain letters, digits, underscores or slashes.
    """
    return sorted(set(re.findall(r"\{([a-zA-Z0-9_/]+)\}", content)))


def render_template(template_content: str, context: dict[str, str]) -> str:
    """Render the template by replacing placeholders using the provided context.

    This function searches for placeholders of the form ``{Name}`` and
    replaces each occurrence with the value from ``context``. If a key is
    missing the global ``MISSING_DATA_PLACEHOLDER`` is used. Numeric strings
    that look like ``10.0`` are rendered as integers (``10``) to improve
    readability in generated markdown.

    Parameters
    ----------
    template_content : str
        The template text containing ``{Placeholders}``.
    context : dict[str, str]
        Mapping from placeholder names to their string values.

    Returns
    -------
    str
        The rendered template with placeholders substituted.
    """

    def format_number_string(val: str) -> str:
        """Normalize numeric-looking strings for readability.

        Parameters
        ----------
        val : str
            Candidate string value from the context.

        Returns
        -------
        str
            Integer-formatted string when input looks like a float with
            zero fractional part (e.g. "10.0" -> "10"), otherwise the
            original value.
        """
        if re.fullmatch(r"-?\d+\.0", val):
            return str(int(float(val)))
        return val

    pattern = re.compile(r"\{([a-zA-Z0-9_/]+)\}")

    def replace_func(match: re.Match[str]) -> str:
        """Replace a placeholder match with its rendered value.

        Parameters
        ----------
        match : re.Match[str]
            The regex match object for a placeholder token.

        Returns
        -------
        str
            Replacement text for the placeholder.
        """
        placeholder_name = match.group(1)
        value = context.get(placeholder_name, MISSING_DATA_PLACEHOLDER)
        return format_number_string(value)

    return pattern.sub(replace_func, template_content)


def load_template_and_placeholders(path: Path) -> tuple[str, list[str]]:
    """Load a template and return its content along with found placeholders.

    Raises
    ------
    ValueError
        If no placeholders are found in the template.
    """
    content = load_template(path)
    placeholders = extract_placeholders_from_template(content)
    if not placeholders:
        raise ValueError("No placeholders found in the template.")
    return content, placeholders
