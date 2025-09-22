"""Data loader and value extraction utilities for school CSV input.

This module encapsulates robust routines for the markdown generation stage that
load Swedish school survey data from semicolon-delimited CSV files. It is
responsible for parsing, cleaning, and retrieving school and survey values
in a defensive, portfolio-compliant way.

Adheres to the School Data Pipeline's separation-of-concerns principle:
no business or presentational logic is present. All configuration is sourced
from src.config.py (e.g., missing data placeholder, survey year priorities).

"""

import csv
from collections.abc import Iterator
from pathlib import Path

from src.config import MISSING_DATA_PLACEHOLDER, SURVEY_YEAR_SUFFIXES_PREFERENCE


def load_school_rows_from_csv(csv_path: Path) -> Iterator[dict[str, str]]:
    """
    Yield cleaned CSV rows as dictionaries for markdown generator.
    
    Opens a semicolon-delimited CSV, strips header/field quotes, and yields
    each row as a normalized mapping from column names to string values.

    Parameters
    ----------
    csv_path : Path
        Path to the UTF-8 encoded CSV file.

    Yields
    ------
    dict[str, str]
        Row with all values as cleaned strings.

    Raises
    ------
    FileNotFoundError
        If the file is missing.
    OSError
        If reading fails.

    Examples
    --------
    >>> from pathlib import Path
    >>> path = Path("data.csv")
    >>> for row in load_school_rows_from_csv(path):
    ...     print(row)
    """
    with csv_path.open("r", encoding="utf-8-sig") as csvfile:
        header_line = csvfile.readline()
        if not header_line:
            return
        headers = [header.strip('"') for header in header_line.strip().split(";")]
        reader = csv.DictReader(csvfile, fieldnames=headers, delimiter=";")
        for raw_row in reader:
            yield {key: str(value).strip('"') for key, value in raw_row.items()}


def get_value_from_row(row: dict[str, str], column_key: str) -> str:
    """
    Extract and sanitize a value for column_key in given row.

    Handles missing, empty, or "N/A" values by returning the missing data
    placeholder configured in src.config.

    Parameters
    ----------
    row : dict[str, str]
        The input row mapping.
    column_key : str
        The column name to extract.

    Returns
    -------
    str
        The cleaned cell value or the missing data placeholder.

    Notes
    -----
    No exception is thrown; always returns a string.

    Examples
    --------
    >>> from src.config import MISSING_DATA_PLACEHOLDER
    >>> get_value_from_row({'x': '1'}, 'x')
    '1'
    >>> get_value_from_row({'x': ''}, 'x') == MISSING_DATA_PLACEHOLDER
    True
    >>> get_value_from_row({'x': 'N/A'}, 'x') == MISSING_DATA_PLACEHOLDER
    True
    """
    value = row.get(column_key)
    if value is None:
        return MISSING_DATA_PLACEHOLDER
    str_value = str(value).strip()
    if str_value == "" or str_value.upper() == "N/A":
        return MISSING_DATA_PLACEHOLDER
    return str_value


def get_survey_answer_value(row: dict[str, str], placeholder: str) -> str:
    """
    Return the latest valid answer for a survey question, searching year suffixes.

    Iterates preferred year suffixes and returns the first non-missing value
    found. Otherwise, returns the missing data placeholder.

    Parameters
    ----------
    row : dict[str, str]
        Row as from school CSV, mapping full column names to values.
    placeholder : str
        Base for survey answer column (e.g., "Q2_").

    Returns
    -------
    str
        The answer value found, or the missing data placeholder.

    Notes
    -----
    The year suffix order follows SURVEY_YEAR_SUFFIXES_PREFERENCE.

    Examples
    --------
    >>> from src.config import SURVEY_YEAR_SUFFIXES_PREFERENCE, MISSING_DATA_PLACEHOLDER
    >>> row = {"Q1_2021": "4.0", "Q1_2020": ""}
    >>> get_survey_answer_value(row, "Q1_")
    '4.0'
    >>> row2 = {"Q1_2021": ""}
    >>> get_survey_answer_value(row2, "Q1_") == MISSING_DATA_PLACEHOLDER
    True
    """
    for year_suffix in SURVEY_YEAR_SUFFIXES_PREFERENCE:
        csv_column_name = f"{placeholder}{year_suffix}"
        data_value = get_value_from_row(row, csv_column_name)
        if data_value != MISSING_DATA_PLACEHOLDER:
            return data_value
    return MISSING_DATA_PLACEHOLDER


def determine_survey_year_for_report(
    row: dict[str, str], template_placeholders: list[str]
) -> str:
    """
    Identify the best survey year for report placeholders from available data.

    Scans preferred year suffixes for any placeholder of the style
    "SurveyAnswerCategory...", and returns the year string if valid data
    is present for that year and placeholder. Otherwise, returns
    the missing data placeholder.

    Parameters
    ----------
    row : dict[str, str]
        Dictionary of school/survey data.
    template_placeholders : list[str]
        Placeholders (without year suffix) found in the template.

    Returns
    -------
    str
        Chosen survey year string (underscores removed), or placeholder.

    Notes
    -----
    Only placeholders starting with "SurveyAnswerCategory" are checked.

    Examples
    --------
    >>> from src.config import MISSING_DATA_PLACEHOLDER
    >>> row = {"SurveyAnswerCategory1_2021": "5.0"}
    >>> determine_survey_year_for_report(row, ["SurveyAnswerCategory1"])
    '2021'
    >>> row2 = {"SurveyAnswerCategory1_2018": ""}
    >>> determine_survey_year_for_report(row2, ["SurveyAnswerCategory1"]) == MISSING_DATA_PLACEHOLDER
    True
    """
    for suffix in SURVEY_YEAR_SUFFIXES_PREFERENCE:
        for placeholder in template_placeholders:
            if placeholder.startswith("SurveyAnswerCategory"):
                csv_col = f"{placeholder}{suffix}"
                if get_value_from_row(row, csv_col) != MISSING_DATA_PLACEHOLDER:
                    return suffix.replace("_", "")
    return MISSING_DATA_PLACEHOLDER
