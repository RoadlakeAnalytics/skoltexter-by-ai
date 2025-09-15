"""Program 3: Website Generation.

Generates a standalone HTML file to display school information. The script
loads school data from a CSV file, combines it with AI-generated markdown
files (converted to HTML), and renders a final website using a template.
The resulting page includes a searchable school list and renders a selected
school's AI-generated description.
"""

import argparse
import json
import logging
from pathlib import Path
from typing import cast

import markdown2
import pandas as pd

from src.config import (
    AI_MARKDOWN_DIR,
    ERROR_DESCRIPTION_HTML,
    FALLBACK_DESCRIPTION_HTML,
    LOG_DIR,
    LOG_FILENAME_GENERATE_WEBSITE,
    LOG_FORMAT,
    NO_DATA_HTML,
    ORIGINAL_CSV_PATH,
    OUTPUT_HTML_FILE,
    WEBSITE_TEMPLATE_PATH,
)

logger = logging.getLogger(__name__)

# Delegate aggregation and rendering to pipeline modules
from src.pipeline.website_generator.data_aggregator import (
    read_school_csv as pipeline_read_school_csv,
    deduplicate_and_format_school_records as pipeline_deduplicate_and_format_school_records,
)
from src.pipeline.website_generator.renderer import (
    clean_html_output as pipeline_clean_html_output,
    generate_final_html as pipeline_generate_html_content,
)


def setup_logging(log_level: str = "INFO", enable_file: bool = True) -> None:
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)
    handlers = [logging.StreamHandler()]
    if enable_file:
        try:
            LOG_DIR.mkdir(exist_ok=True)
            handlers.insert(0, logging.FileHandler(LOG_DIR / LOG_FILENAME_GENERATE_WEBSITE, mode="a"))
        except Exception:
            pass
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO), format=LOG_FORMAT, handlers=handlers)


def read_school_csv(csv_path: Path) -> pd.DataFrame:
    return pipeline_read_school_csv(csv_path)


def get_school_description_html(school_code: str, ai_markdown_dir: Path) -> str:
    markdown_file_path = ai_markdown_dir / f"{school_code}_ai_description.md"
    if not markdown_file_path.exists():
        return FALLBACK_DESCRIPTION_HTML
    try:
        markdown_text = markdown_file_path.read_text(encoding="utf-8")
        description_html = cast(str, markdown2.markdown(markdown_text, extras=["tables", "fenced-code-blocks"]))
        return pipeline_clean_html_output(description_html)
    except Exception:
        return ERROR_DESCRIPTION_HTML


def load_school_data(csv_path: Path, ai_markdown_dir: Path) -> list[dict[str, str]]:
    dataframe = pipeline_read_school_csv(csv_path)
    if dataframe.empty:
        return []
    schools = pipeline_deduplicate_and_format_school_records(dataframe)
    for s in schools:
        s["ai_description_html"] = get_school_description_html(s["id"], ai_markdown_dir)
    return schools


def generate_html_content(school_list_json: str) -> str:
    return pipeline_generate_html_content(json.loads(school_list_json), WEBSITE_TEMPLATE_PATH)


def write_html_output(html_content: str, output_file: Path) -> None:
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(html_content, encoding="utf-8")
    except Exception:
        logger.exception("Failed to write HTML output")


def write_no_data_html(output_file: Path) -> None:
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(NO_DATA_HTML, encoding="utf-8")
    except Exception:
        logger.exception("Failed to write fallback HTML")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a standalone HTML website for school information.")
    parser.add_argument("--csv", type=Path, default=ORIGINAL_CSV_PATH)
    parser.add_argument("--markdown_dir", type=Path, default=AI_MARKDOWN_DIR)
    parser.add_argument("--output", type=Path, default=OUTPUT_HTML_FILE)
    parser.add_argument("--log-level", type=str, default="INFO")
    args = parser.parse_args()
    setup_logging(args.log_level, enable_file=not bool(__import__('os').environ.get('DISABLE_FILE_LOGS')))
    schools = load_school_data(args.csv, args.markdown_dir)
    if not schools:
        write_no_data_html(args.output)
        return
    html = generate_html_content(json.dumps(schools, ensure_ascii=False))
    write_html_output(html, args.output)


if __name__ == "__main__":
    main()

