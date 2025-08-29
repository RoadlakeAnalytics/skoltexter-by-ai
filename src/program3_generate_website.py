"""Program 3: Website Generation

Generates a standalone HTML file to display school information.
Loads school data from a CSV file and combines it with AI-generated markdown (converted to HTML).
The resulting webpage features a dropdown menu for school selection and displays the school's AI-generated description.
"""

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import markdown2  # type: ignore

from src.config import (
    ORIGINAL_CSV_PATH,
    AI_MARKDOWN_DIR,
    OUTPUT_HTML_DIR,
    OUTPUT_HTML_FILE,
    FALLBACK_SCHOOL_NAME_FORMAT,
    FALLBACK_DESCRIPTION_HTML,
    ERROR_DESCRIPTION_HTML,
    NO_DATA_HTML,
    LOG_DIR,
    LOG_FORMAT,
    LOG_FILENAME_GENERATE_WEBSITE,
    WEBSITE_TEMPLATE_PATH,
)

logger = logging.getLogger(__name__)


def setup_logging(log_level: str = "INFO") -> None:
    """Configure logging for the website generation script.

    Args:
        log_level: Logging level as a string (e.g., "INFO", "DEBUG").
    """
    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(LOG_DIR / LOG_FILENAME_GENERATE_WEBSITE, mode="a"),
            logging.StreamHandler(),
        ],
    )


def read_school_csv(csv_path: Path) -> pd.DataFrame:
    """Read the school CSV file and return a DataFrame with required columns.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        DataFrame with 'SchoolCode' and 'SchoolName' columns.
    """
    try:
        dataframe = pd.read_csv(
            csv_path,
            delimiter=";",
            usecols=["SchoolCode", "SchoolName"],
            dtype={"SchoolCode": str, "SchoolName": str},
        ).fillna({"SchoolCode": "", "SchoolName": ""})
    except FileNotFoundError:
        logger.error(f"CSV file not found at: {csv_path.resolve()}")
        return pd.DataFrame()
    except ValueError as error:
        logger.error(
            f"Error reading CSV file (check columns 'SchoolCode', 'SchoolName'): {error}"
        )
        return pd.DataFrame()
    except Exception as error:
        logger.error(
            f"An unexpected error occurred while reading CSV {csv_path.resolve()}: {error}"
        )
        return pd.DataFrame()
    if dataframe.empty:
        logger.warning(f"CSV file {csv_path.resolve()} is empty or only headers.")
    return dataframe


def deduplicate_and_format_school_records(
    dataframe: pd.DataFrame,
) -> List[Dict[str, str]]:
    """Deduplicate school records and apply fallback names if needed.

    Args:
        dataframe: DataFrame with school data.

    Returns:
        List of dictionaries with 'id' and 'name' for each school.
    """
    schools_data: List[Dict[str, str]] = []
    processed_school_codes = set()

    for _, school_row in dataframe.iterrows():
        school_code = str(school_row.get("SchoolCode", "")).strip()
        school_name = str(school_row.get("SchoolName", "")).strip()

        if not school_code:
            logger.warning("Found a row in CSV with missing SchoolCode. Skipping.")
            continue

        if school_code in processed_school_codes:
            logger.warning(
                f"Duplicate SchoolCode '{school_code}' found in CSV. Using first instance."
            )
            continue
        processed_school_codes.add(school_code)

        if not school_name:
            school_name = FALLBACK_SCHOOL_NAME_FORMAT.format(school_code=school_code)
            logger.warning(
                f"SchoolCode '{school_code}' has no SchoolName. Using fallback: '{school_name}'."
            )

        schools_data.append({"id": school_code, "name": school_name})

    if not schools_data:
        logger.warning("No school data could be loaded or processed.")
    else:
        logger.info(f"Successfully loaded and prepared data for {len(schools_data)} schools.")

    schools_data.sort(key=lambda school: school["name"])
    return schools_data


def get_school_description_html(
    school_code: str, ai_markdown_dir: Path
) -> str:
    """Read and convert the AI-generated markdown for a school to cleaned HTML.

    Args:
        school_code: The school code.
        ai_markdown_dir: Directory containing AI-generated markdown files.

    Returns:
        Cleaned HTML string for the school's description.
    """
    markdown_file_path = ai_markdown_dir / f"{school_code}_ai_description.md"
    if not markdown_file_path.exists():
        logger.warning(
            f"AI-generated markdown file not found for {school_code} at {markdown_file_path.resolve()}."
        )
        return FALLBACK_DESCRIPTION_HTML

    try:
        markdown_text = markdown_file_path.read_text(encoding="utf-8")
        description_html = markdown2.markdown(
            markdown_text, extras=["tables", "fenced-code-blocks"]
        )
        description_html = clean_html_output(description_html)
        return description_html
    except Exception as error:
        logger.error(
            f"Error reading or converting markdown for {school_code} from {markdown_file_path.resolve()}: {error}"
        )
        return ERROR_DESCRIPTION_HTML


def clean_html_output(html_content: str) -> str:
    """Clean up HTML output from markdown conversion.

    Args:
        html_content: Raw HTML string.

    Returns:
        Cleaned HTML string.
    """
    html_content = re.sub(r"<p>\s*</p>", "", html_content)
    html_content = re.sub(r"<p>&nbsp;</p>", "", html_content)
    html_content = re.sub(r"<p><br\s*/?>\s*</p>", "", html_content)
    html_content = re.sub(
        r"(<h[1-6][^>]*>.*?</h[1-6]>)\s*<p>\s*</p>", r"\1", html_content
    )
    html_content = re.sub(
        r"(<h[1-6][^>]*>.*?</h[1-6]>)\s*<br\s*/?>\s*", r"\1\n", html_content
    )
    html_content = re.sub(r"(<br\s*/?>\s*){2,}", "<br>", html_content)
    html_content = re.sub(
        r"(<h[1-6][^>]*>.*?</h[1-6]>)\s*<br\s*/?>", r"\1", html_content
    )
    html_content = re.sub(r"<p>\s*<br\s*/?>\s*</p>", "", html_content)
    html_content = re.sub(r"\n\s*\n\s*\n+", "\n\n", html_content)
    html_content = re.sub(r">\s+<", "><", html_content)
    html_content = html_content.strip()
    return html_content


def load_school_data(
    csv_path: Path, ai_markdown_dir: Path
) -> List[Dict[str, str]]:
    """Load school data and combine with AI-generated descriptions.

    Args:
        csv_path: Path to the CSV file.
        ai_markdown_dir: Directory containing AI-generated markdown files.

    Returns:
        List of dictionaries with 'id', 'name', and 'ai_description_html' for each school.
    """
    logger.info(f"Loading school master data from CSV: {csv_path.resolve()}")
    dataframe = read_school_csv(csv_path)
    if dataframe.empty:
        return []

    schools_data = deduplicate_and_format_school_records(dataframe)
    for school in schools_data:
        school["ai_description_html"] = get_school_description_html(
            school["id"], ai_markdown_dir
        )
    return schools_data


def generate_html_content(school_list_json: str) -> str:
    """Generate the complete HTML document as a string using the external template.

    Args:
        school_list_json: A JSON string representing the list of school data.

    Returns:
        The complete HTML document as a string.
    """
    with WEBSITE_TEMPLATE_PATH.open("r", encoding="utf-8") as template_file:
        html_template = template_file.read()
    return html_template.replace("{school_list_json}", school_list_json)


def write_html_output(html_content: str, output_file: Path) -> None:
    """Write the generated HTML content to the output file.

    Args:
        html_content: The HTML content to write.
        output_file: Path to the output HTML file.
    """
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(html_content, encoding="utf-8")
        logger.info(f"Successfully generated website: {output_file.resolve()}")
    except IOError as error:
        logger.error(f"Failed to write HTML output to file {output_file.resolve()}: {error}")
    except Exception as error:
        logger.error(
            f"An unexpected error occurred during HTML file writing: {error}", exc_info=True
        )


def write_no_data_html(output_file: Path) -> None:
    """Write a minimal HTML page indicating no data is available.

    Args:
        output_file: Path to the output HTML file.
    """
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(NO_DATA_HTML, encoding="utf-8")
        logger.info(f"Generated a fallback HTML page due to no data: {output_file.resolve()}")
    except IOError as error:
        logger.error(f"Failed to write fallback HTML file: {error}")


def main() -> None:
    """Main function to orchestrate the generation of the website."""
    import os

    parser = argparse.ArgumentParser(
        description="Generate a standalone HTML website for school information."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=ORIGINAL_CSV_PATH,
        help="Path to the school data CSV file.",
    )
    parser.add_argument(
        "--markdown_dir",
        type=Path,
        default=AI_MARKDOWN_DIR,
        help="Directory containing AI-generated markdown files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_HTML_FILE,
        help="Path to the output HTML file.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=os.environ.get("LOG_LEVEL", "INFO"),
        help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default=os.environ.get("LANG_UI", "en"),
        help="Language code for output/logs (en or sv).",
    )
    args = parser.parse_args()

    setup_logging(args.log_level)
    logger.info("="*50)
    logger.info("Starting Program 3: Website Generation")
    logger.info("="*50)
    # Language argument is accepted for future-proofing; not used in this script

    logger.info("Starting website generation process...")

    schools_data = load_school_data(args.csv, args.markdown_dir)
    if not schools_data:
        logger.error("No school data loaded. HTML generation will be skipped.")
        write_no_data_html(args.output)
        return

    schools_json_for_html = json.dumps(schools_data, ensure_ascii=False)
    full_html_output = generate_html_content(schools_json_for_html)
    write_html_output(full_html_output, args.output)


if __name__ == "__main__":
    main()