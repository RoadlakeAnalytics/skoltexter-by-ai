"""Website generator package.

Provides data aggregation and renderer helpers.
"""

from .data_aggregator import (
    deduplicate_and_format_school_records,
    load_school_data,
    read_school_csv,
)
from .renderer import (
    clean_html_output,
    generate_final_html,
    get_school_description_html,
    write_html_output,
    write_no_data_html,
)

__all__ = [
    "read_school_csv",
    "deduplicate_and_format_school_records",
    "load_school_data",
    "get_school_description_html",
    "clean_html_output",
    "generate_final_html",
    "write_html_output",
    "write_no_data_html",
]
