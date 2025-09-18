"""Templating utilities for markdown generation."""

import re
from pathlib import Path

from src.config import MISSING_DATA_PLACEHOLDER


def load_template(path: Path) -> str:
    """Load the template file contents as a string.

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
        if re.fullmatch(r"-?\d+\.0", val):
            return str(int(float(val)))
        return val

    pattern = re.compile(r"\{([a-zA-Z0-9_/]+)\}")

    def replace_func(match: re.Match) -> str:
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
