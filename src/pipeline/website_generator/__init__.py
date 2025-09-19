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
    "clean_html_output",
    "deduplicate_and_format_school_records",
    "generate_final_html",
    "get_school_description_html",
    "load_school_data",
    "read_school_csv",
    "write_html_output",
    "write_no_data_html",
]
