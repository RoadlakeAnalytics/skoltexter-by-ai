"""Templating utilities for markdown generation.
"""

import re
from pathlib import Path

from src.config import MISSING_DATA_PLACEHOLDER


def load_template(path: Path) -> str:
    with path.open("r", encoding="utf-8") as fh:
        return fh.read()


def extract_placeholders_from_template(content: str) -> list[str]:
    return sorted(set(re.findall(r"\{([a-zA-Z0-9_/]+)\}", content)))


def render_template(template_content: str, context: dict[str, str]) -> str:
    def format_number_string(val: str) -> str:
        if re.fullmatch(r"-?\d+\.0", val):
            return str(int(float(val)))
        return val

    pattern = re.compile(r"\{([a-zA-Z0-9_/]+)\}")

    def replace_func(match: re.Match[str]) -> str:
        placeholder_name = match.group(1)
        value = context.get(placeholder_name, MISSING_DATA_PLACEHOLDER)
        return format_number_string(value)

    return pattern.sub(replace_func, template_content)


def load_template_and_placeholders(path: Path) -> tuple[str, list[str]]:
    content = load_template(path)
    placeholders = extract_placeholders_from_template(content)
    if not placeholders:
        raise ValueError("No placeholders found in the template.")
    return content, placeholders

