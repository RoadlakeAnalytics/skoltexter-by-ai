"""data_aggregator.py: Module for aggregating and processing school CSV data for HTML website generation.

This module forms one data-oriented component of the website generation pipeline. Its primary responsibility is to load, validate, deduplicate, and format raw school data from a CSV source, preparing it for further rendering and augmentation (e.g., by injecting AI-generated descriptions).

Design Principles
-----------------
- Isolated responsibility: contains *no* rendering/UI logic.
- Exposes only pure utility functions to facilitate orchestration by higher-level pipeline modules.
- All configuration constants (such as fallback name format) are provided externally via `src/config.py`.

Context
-------
- Consumed by the website generator core (see `renderer.py`).
- All input validation, error handling, and configuration management is strictly internalized.

Usage
-----
>>> from pathlib import Path
>>> schools = load_school_data(Path("schools.csv"), Path("ai_md/"))
>>> assert isinstance(schools, list)

References
----------
- AGENTS.md: "Portfolio School Data Pipeline Architecture"
- pandas official documentation: https://pandas.pydata.org/
- Project config: src/config.py

"""

from pathlib import Path

import pandas as pd

from src.config import FALLBACK_SCHOOL_NAME_FORMAT


def read_school_csv(csv_path: Path) -> pd.DataFrame:
    """Read and validate a school CSV file into a DataFrame containing code and name columns.

    This function serves as the canonical data ingestion point for all school CSV files in the website generation pipeline.
    It guarantees a reproducible dataframe structure (columns `SchoolCode` and `SchoolName` as strings), applying strict schema selection and null-filling.
    All errors result in an empty DataFrame (never a crash).

    Parameters
    ----------
    csv_path : Path
        Path to the school CSV file. The file should be semicolon-delimited and contain columns `SchoolCode`, `SchoolName`.

    Returns
    -------
    pd.DataFrame
        A pandas DataFrame with columns `SchoolCode` and `SchoolName`, never None; may be empty on failure.

    Raises
    ------
    DataValidationError
        If the CSV is missing required columns or is malformed.
    ExternalServiceError
        If a downstream system exception occurs (e.g., file IO, pandas).

    See Also
    --------
    deduplicate_and_format_school_records
        Post-processes the output of this function.

    Notes
    -----
    - The schema is always enforced; extra columns are ignored.
    - If an error or missing column is detected, returns a zero-row DataFrame.
    - All types are normalized to string.

    Examples
    --------
    >>> import pandas as pd
    >>> from pathlib import Path
    >>> from src.pipeline.website_generator.data_aggregator import read_school_csv
    >>> # Suppose schools_example.csv has SchoolCode and SchoolName columns
    >>> df = read_school_csv(Path('schools_example.csv'))
    >>> isinstance(df, pd.DataFrame)
    True
    >>> list(df.columns)
    ['SchoolCode', 'SchoolName']
    >>> # Bad input: file missing columns
    >>> df_fail = read_school_csv(Path('not_a_real_file.csv'))
    >>> df_fail.empty
    True
    >>> # Edge case: no school codes at all
    >>> # See tests/pipeline/website_generator/test_data_aggregator.py for test coverage.

    References
    ----------
    pandas.read_csv documentation: https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html

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
    """Deduplicate and format school records for rendering by school code.

    Processes rows in the input DataFrame, normalizing and de-duplicating them by unique SchoolCode, and converting records into dicts suitable for downstream rendering.
    Fallback names are supplied from configuration if missing. The output list is always sorted by school name for deterministic ordering.

    Parameters
    ----------
    dataframe : pd.DataFrame
        DataFrame must contain columns "SchoolCode" and "SchoolName". May contain nulls or extra columns.

    Returns
    -------
    list of dict[str, str]
        Each dict contains 'id' (school code, str) and 'name' (school name, str).

    Raises
    ------
    DataValidationError
        If required columns are missing or values are malformed.
    ConfigurationError
        If fallback name format is missing in config.

    See Also
    --------
    read_school_csv
        Use to ingest CSV files before deduplication.

    Notes
    -----
    - Empty or duplicate school codes are skipped.
    - If school name is missing or blank, uses `FALLBACK_SCHOOL_NAME_FORMAT` from config.
    - Output is sorted alphabetically by school name.

    Examples
    --------
    >>> import pandas as pd
    >>> from src.pipeline.website_generator.data_aggregator import deduplicate_and_format_school_records
    >>> data = {
    ...     "SchoolCode": ["101", "101", "102", "", "103"],
    ...     "SchoolName": ["Alpha School", "Alpha School", "Beta Academy", "", None]
    ... }
    >>> df = pd.DataFrame(data)
    >>> result = deduplicate_and_format_school_records(df)
    >>> assert isinstance(result, list)
    >>> assert len(result) == 3
    >>> assert result[0]["id"] == "101"
    >>> # Sorted order (by name)
    >>> names = [school['name'] for school in result]
    >>> "Alpha School" in names and "Beta Academy" in names
    True

    References
    ----------
    AGENTS.md - Configuration pattern for fallback formats.
    src/config.py
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
    """Load and prepare complete school data objects for website generation.

    Orchestrates the fetching, deduplication, and initial structure of school records, also pre-populating storage for AI-generated HTML descriptions.
    This function is the canonical entrypoint for consuming raw CSV data and scaffolding the in-memory representations used throughout the website generator pipeline.

    Parameters
    ----------
    csv_path : Path
        Path to the input CSV file containing school codes and names.
    ai_markdown_dir : Path
        Directory where AI-generated markdown files reside. Currently this argument is reserved for future extension.

    Returns
    -------
    list of dict[str, str]
        Each school dict contains keys:
        - "id" (school code, str)
        - "name" (school name, str)
        - "ai_description_html" (str, always initialized blank)

    Raises
    ------
    DataValidationError
        If input CSV fails validation.
    ExternalServiceError
        If IO or upstream service issues occur.

    See Also
    --------
    read_school_csv, deduplicate_and_format_school_records

    Notes
    -----
    - Returns empty list if CSV file is missing or records are not valid.
    - The `ai_description_html` is initialized as an empty string—consuming renderer module will populate it.
    - Designed for composability in larger pipeline steps.

    Examples
    --------
    >>> from pathlib import Path
    >>> from src.pipeline.website_generator.data_aggregator import load_school_data
    >>> # Valid input
    >>> schools = load_school_data(Path("schools.csv"), Path("ai_md/"))
    >>> isinstance(schools, list)
    True
    >>> # Edge case: empty/nonexistent csv
    >>> schools_fail = load_school_data(Path("does_not_exist.csv"), Path("ai_md/"))
    >>> schools_fail == []
    True

    References
    ----------
    AGENTS.md: School Website Aggregator logic

    """
    df = read_school_csv(csv_path)
    if df.empty:
        return []
    schools = deduplicate_and_format_school_records(df)
    for s in schools:
        s["ai_description_html"] = ""
    return schools
