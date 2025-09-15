"""CSV data loader for the markdown generator.
"""

import csv
from pathlib import Path

from src.config import MISSING_DATA_PLACEHOLDER, SURVEY_YEAR_SUFFIXES_PREFERENCE


def load_school_rows_from_csv(csv_path: Path):
    with csv_path.open("r", encoding="utf-8-sig") as csvfile:
        header_line = csvfile.readline()
        if not header_line:
            return
        headers = [header.strip('"') for header in header_line.strip().split(";")]
        reader = csv.DictReader(csvfile, fieldnames=headers, delimiter=";")
        for raw_row in reader:
            yield {key: str(value).strip('"') for key, value in raw_row.items()}


def get_value_from_row(row: dict[str, str], column_key: str) -> str:
    value = row.get(column_key)
    if value is None:
        return MISSING_DATA_PLACEHOLDER
    str_value = str(value).strip()
    if str_value == "" or str_value.upper() == "N/A":
        return MISSING_DATA_PLACEHOLDER
    return str_value


def get_survey_answer_value(row: dict[str, str], placeholder: str) -> str:
    for year_suffix in SURVEY_YEAR_SUFFIXES_PREFERENCE:
        csv_column_name = f"{placeholder}{year_suffix}"
        data_value = get_value_from_row(row, csv_column_name)
        if data_value != MISSING_DATA_PLACEHOLDER:
            return data_value
    return MISSING_DATA_PLACEHOLDER


def determine_survey_year_for_report(row: dict[str, str], template_placeholders: list[str]) -> str:
    for suffix in SURVEY_YEAR_SUFFIXES_PREFERENCE:
        for placeholder in template_placeholders:
            if placeholder.startswith("SurveyAnswerCategory"):
                csv_col = f"{placeholder}{suffix}"
                if get_value_from_row(row, csv_col) != MISSING_DATA_PLACEHOLDER:
                    return suffix.replace("_", "")
    return MISSING_DATA_PLACEHOLDER

