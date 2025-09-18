"""Aggregate CSV and AI markdown data for website generation."""

from pathlib import Path

import pandas as pd

from src.config import FALLBACK_SCHOOL_NAME_FORMAT


def read_school_csv(csv_path: Path) -> pd.DataFrame:
    """Read the CSV file and return a DataFrame with SchoolCode and SchoolName.

    Parameters
    ----------
    csv_path : Path
        Path to the semicolon-delimited CSV file.

    Returns
    -------
    pd.DataFrame
        DataFrame with `SchoolCode` and `SchoolName` columns or empty DataFrame on error.
    """
    try:
        dataframe = pd.read_csv(
            csv_path,
            delimiter=";",
            usecols=["SchoolCode", "SchoolName"],
            dtype={"SchoolCode": str, "SchoolName": str},
        ).fillna({"SchoolCode": "", "SchoolName": ""})
    except Exception:
        return pd.DataFrame()
    return dataframe


def deduplicate_and_format_school_records(
    dataframe: pd.DataFrame,
) -> list[dict[str, str]]:
    """Deduplicate rows by school code and format for rendering.

    Parameters
    ----------
    dataframe : pd.DataFrame
        DataFrame containing `SchoolCode` and `SchoolName` columns.

    Returns
    -------
    list[dict[str, str]]
        List of dicts with `id` and `name` keys representing schools.
    """
    schools_data: list[dict[str, str]] = []
    processed_school_codes = set()
    for _, school_row in dataframe.iterrows():
        school_code = str(school_row.get("SchoolCode", "")).strip()
        school_name = str(school_row.get("SchoolName", "")).strip()
        if not school_code:
            continue
        if school_code in processed_school_codes:
            continue
        processed_school_codes.add(school_code)
        if not school_name:
            school_name = FALLBACK_SCHOOL_NAME_FORMAT.format(school_code=school_code)
        schools_data.append({"id": school_code, "name": school_name})
    schools_data.sort(key=lambda school: school["name"])
    return schools_data


def load_school_data(csv_path: Path, ai_markdown_dir: Path) -> list[dict[str, str]]:
    """Load school records from CSV and prepare data structure for rendering.

    Parameters
    ----------
    csv_path : Path
        Path to the input CSV file.
    ai_markdown_dir : Path
        Directory where AI-generated markdown files are stored.

    Returns
    -------
    list[dict[str, str]]
        List of school dictionaries including an `ai_description_html` key.
    """
    df = read_school_csv(csv_path)
    if df.empty:
        return []
    schools = deduplicate_and_format_school_records(df)
    for s in schools:
        s["ai_description_html"] = ""
    return schools
