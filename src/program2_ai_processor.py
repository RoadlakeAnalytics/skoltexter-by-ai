"""AI Processor for School Descriptions

Processes markdown files with school data, sends them to Azure OpenAI for detailed description generation,
handles API communication, rate limiting, retries, and saves both cleaned markdown and raw JSON responses.

All configuration and magic values are imported from config.py.
"""

import argparse
import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, Optional, Tuple, List

import aiohttp
from aiolimiter import AsyncLimiter
from dotenv import load_dotenv
from tqdm.asyncio import tqdm_asyncio

from src.config import (
    PROJECT_ROOT,
    LOG_DIR,
    LOG_FORMAT,
    LOG_FILENAME_AI_PROCESSOR,
    AI_PROCESSED_MARKDOWN_SUBDIR,
    AI_RAW_RESPONSES_SUBDIR,
    AI_PROCESSED_FILENAME_SUFFIX,
    AI_RAW_RESPONSE_FILENAME_SUFFIX,
    AI_FAILED_RESPONSE_FILENAME_SUFFIX,
    DEFAULT_INPUT_MARKDOWN_DIR,
    DEFAULT_OUTPUT_BASE_DIR,
    MAX_CONCURRENT_REQUESTS,
    TARGET_RPM,
    MAX_RETRIES,
    BACKOFF_FACTOR,
    RETRY_SLEEP_ON_429,
    TEMPERATURE,
    REQUEST_TIMEOUT,
    DEFAULT_DEPLOYMENT_NAME,
    DEFAULT_API_VERSION,
    AI_PAYLOAD_MAX_TOKENS,
    AI_PROMPT_TEMPLATE_PATH,
)

# --- Logging Setup ---
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_DIR / LOG_FILENAME_AI_PROCESSOR, mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class OpenAIConfig:
    """Configuration for Azure OpenAI API settings."""

    def __init__(self) -> None:
        """Initialize configuration from environment variables and config.py constants."""
        self._load_environment()
        self._setup_endpoints()
        self._setup_parameters()

    def _load_environment(self) -> None:
        """Load environment variables from .env file or system environment."""
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Loaded environment variables from: {env_path}")
        else:
            logger.warning(f".env file not found at {env_path}. Using system environment variables.")

        self.api_key = os.getenv("AZURE_API_KEY") or os.getenv("API_KEY")
        self.endpoint_base = os.getenv("AZURE_ENDPOINT_BASE")
        self.deployment_name = os.getenv("GPT4O_DEPLOYMENT_NAME", DEFAULT_DEPLOYMENT_NAME)
        self.api_version = os.getenv("AZURE_API_VERSION", DEFAULT_API_VERSION)

        if not self.api_key:
            logger.error("API_KEY (or AZURE_API_KEY) environment variable is required but not found.")
            raise ValueError("API_KEY (or AZURE_API_KEY) environment variable is required.")
        if not self.endpoint_base and "AZURE_API_KEY" in os.environ:
            logger.error("AZURE_ENDPOINT_BASE environment variable is required for Azure OpenAI but not found.")
            raise ValueError("AZURE_ENDPOINT_BASE environment variable is required for Azure OpenAI.")
        elif not self.endpoint_base:
            logger.warning("AZURE_ENDPOINT_BASE is not set. This might be an issue if using Azure.")

    def _setup_endpoints(self) -> None:
        """Set up API endpoints based on loaded configuration."""
        if self.endpoint_base:
            self.gpt4o_endpoint = (
                f"{self.endpoint_base.rstrip('/')}/openai/deployments/{self.deployment_name}/"
                f"chat/completions?api-version={self.api_version}"
            )
            logger.info(f"Using Azure GPT-4o endpoint: {self.gpt4o_endpoint}")
        else:
            self.gpt4o_endpoint = ""

    def _setup_parameters(self) -> None:
        """Set up operational parameters from environment or config.py defaults."""
        self.max_concurrent_requests = int(os.getenv("MAX_CONCURRENT_REQUESTS", MAX_CONCURRENT_REQUESTS))
        self.target_rpm = int(os.getenv("TARGET_RPM", TARGET_RPM))
        self.max_retries = int(os.getenv("MAX_RETRIES", MAX_RETRIES))
        self.backoff_factor = float(os.getenv("BACKOFF_FACTOR", BACKOFF_FACTOR))
        self.retry_sleep_on_429 = int(os.getenv("RETRY_SLEEP_ON_429", RETRY_SLEEP_ON_429))
        self.temperature = float(os.getenv("TEMPERATURE", TEMPERATURE))
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", REQUEST_TIMEOUT))
        logger.info(
            f"Operational parameters: Max Concurrent Requests={self.max_concurrent_requests}, "
            f"Target RPM={self.target_rpm}, Max Retries={self.max_retries}, "
            f"Temperature={self.temperature}, Request Timeout={self.request_timeout}s"
        )


class SchoolDescriptionProcessor:
    """Processes school markdown files through an AI API."""

    def __init__(self, config: OpenAIConfig, input_dir: Path, output_dir_base: Path) -> None:
        """Initialize the processor and load the AI prompt template.

        Args:
            config: OpenAI configuration object.
            input_dir: Directory containing input markdown files.
            output_dir_base: Base directory for processed output files.
        """
        self.config = config
        self.input_dir = Path(input_dir)
        self.markdown_output_dir = output_dir_base / AI_PROCESSED_MARKDOWN_SUBDIR
        self.json_output_dir = output_dir_base / AI_RAW_RESPONSES_SUBDIR
        self.markdown_output_dir.mkdir(parents=True, exist_ok=True)
        self.json_output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized SchoolDescriptionProcessor with input: {self.input_dir.resolve()}, "
                    f"markdown output: {self.markdown_output_dir.resolve()}, "
                    f"json output: {self.json_output_dir.resolve()}")

        # Load the AI prompt template once
        self.prompt_template = self._load_prompt_template(AI_PROMPT_TEMPLATE_PATH)

    @staticmethod
    def _load_prompt_template(template_path: Path) -> str:
        """Load the AI prompt template from file.

        Args:
            template_path: Path to the template file.

        Returns:
            The template content as a string.
        """
        with template_path.open("r", encoding="utf-8") as file_handle:
            return file_handle.read()

    def _parse_prompt_template(self, school_data: str) -> dict:
        """Parse the loaded prompt template and substitute school data.

        Args:
            school_data: Markdown-formatted data for a single school.

        Returns:
            Dictionary for the OpenAI API payload.
        """
        # Substitute {school_data} in the template
        prompt_filled = self.prompt_template.replace("{school_data}", school_data)
        # Split into system and user messages
        # Expecting markers "SYSTEM:" and "USER:" at the start of lines
        system_marker = "SYSTEM:"
        user_marker = "USER:"
        system_start = prompt_filled.find(system_marker)
        user_start = prompt_filled.find(user_marker)
        if system_start == -1 or user_start == -1:
            logger.error("Prompt template missing SYSTEM: or USER: markers.")
            raise ValueError("Prompt template must contain 'SYSTEM:' and 'USER:' markers.")
        system_content = prompt_filled[system_start + len(system_marker):user_start].strip()
        user_content = prompt_filled[user_start + len(user_marker):].strip()
        return {
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": AI_PAYLOAD_MAX_TOKENS,
            "temperature": self.config.temperature,
        }

    def _clean_ai_response(self, content: str) -> str:
        """Remove markdown code fences from the AI-generated content.

        Args:
            content: The raw string content from the AI response.

        Returns:
            The cleaned string content.
        """
        cleaned_content = content.strip()
        fence_pattern = re.compile(r"^\s*```(?:[a-zA-Z0-9]+\s*)?\n?(.*?)\n?```\s*$", re.DOTALL | re.IGNORECASE)
        match = fence_pattern.match(cleaned_content)
        if match:
            return match.group(1).strip()
        if cleaned_content.startswith("```markdown"):
            cleaned_content = cleaned_content[len("```markdown"):].lstrip()
        elif cleaned_content.startswith("```"):
            cleaned_content = cleaned_content[len("```"):].lstrip()
        if cleaned_content.endswith("```"):
            cleaned_content = cleaned_content[:-len("```")].rstrip()
        return cleaned_content

    def create_ai_payload(self, school_data: str) -> dict:
        """Create the payload for the OpenAI API request using the externalized template.

        Args:
            school_data: Markdown-formatted data for a single school.

        Returns:
            Dictionary representing the JSON payload for the API request.
        """
        return self._parse_prompt_template(school_data)

    async def call_openai_api(
        self,
        session: aiohttp.ClientSession,
        payload: dict,
        school_id: str,
        rate_limiter: AsyncLimiter,
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        """Make an asynchronous API call to OpenAI with rate limiting, retries, and error handling.

        Args:
            session: The aiohttp client session.
            payload: The JSON payload for the API request.
            school_id: The identifier for the school being processed (for logging).
            rate_limiter: An AsyncLimiter instance to control request rate.

        Returns:
            Tuple of (success, cleaned AI-generated description, raw JSON response or error dict).
        """
        if not self.config.gpt4o_endpoint:
            logger.error(f"OpenAI endpoint is not configured. Cannot call API for {school_id}.")
            return False, None, {"error_type": "ConfigurationError", "message": "OpenAI endpoint not set."}

        headers = {
            "Content-Type": "application/json",
            "api-key": self.config.api_key,
        }

        for attempt_number in range(self.config.max_retries + 1):
            try:
                async with rate_limiter:
                    async with session.post(
                        self.config.gpt4o_endpoint,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=self.config.request_timeout)
                    ) as response:
                        response_status = response.status
                        response_text = await response.text()

                        if response_status == 200:
                            try:
                                response_json = json.loads(response_text)
                                if not response_json.get("choices"):
                                    logger.error(
                                        f"API response for {school_id} (Attempt {attempt_number + 1}) "
                                        f"missing 'choices' field or empty: {response_json}"
                                    )
                                    if attempt_number < self.config.max_retries:
                                        await asyncio.sleep(self.config.backoff_factor ** attempt_number)
                                        continue
                                    return False, None, response_json
                                content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                                if not content:
                                    logger.warning(
                                        f"Empty content in API response for {school_id} (Attempt {attempt_number + 1}). "
                                        f"Full response: {response_json}"
                                    )
                                    if attempt_number < self.config.max_retries:
                                        await asyncio.sleep(self.config.backoff_factor ** attempt_number)
                                        continue
                                    logger.error(f"Empty content from API for {school_id} after {self.config.max_retries + 1} attempts.")
                                    return False, None, response_json
                                cleaned_content = self._clean_ai_response(content)
                                return True, cleaned_content, response_json
                            except json.JSONDecodeError:
                                logger.error(
                                    f"Could not parse JSON response for {school_id} (Attempt {attempt_number + 1}): "
                                    f"{response_text[:200]}..."
                                )
                                return False, None, {"raw_response_text": response_text}
                        elif response_status == 429:
                            logger.warning(
                                f"Rate limit hit for {school_id} (Attempt {attempt_number + 1}). "
                                f"Waiting {self.config.retry_sleep_on_429 * (attempt_number + 1)}s."
                            )
                            await asyncio.sleep(self.config.retry_sleep_on_429 * (attempt_number + 1))
                        else:
                            error_message = response_text[:500]
                            logger.error(
                                f"API error for {school_id} (Attempt {attempt_number + 1}): Status {response_status}. "
                                f"Response: {error_message}."
                            )
                            if attempt_number < self.config.max_retries:
                                await asyncio.sleep(self.config.backoff_factor ** attempt_number)
                            else:
                                logger.error(f"API error persists for {school_id} after {self.config.max_retries + 1} attempts.")
                                return False, None, {"status_code": response_status, "error_body": response_text}
            except aiohttp.ClientError as error:
                logger.error(f"Network error for {school_id} (Attempt {attempt_number + 1}): {error}.")
                if attempt_number < self.config.max_retries:
                    await asyncio.sleep(self.config.backoff_factor ** attempt_number)
                else:
                    logger.error(f"Network error persists for {school_id} after {self.config.max_retries + 1} attempts.")
                    return False, None, {"error_type": "ClientError", "message": str(error)}
            except asyncio.TimeoutError:
                logger.error(f"Request timeout for {school_id} (Attempt {attempt_number + 1}).")
                if attempt_number < self.config.max_retries:
                    await asyncio.sleep(self.config.backoff_factor ** attempt_number)
                else:
                    logger.error(f"Timeout persists for {school_id} after {self.config.max_retries + 1} attempts.")
                    return False, None, {"error_type": "TimeoutError"}
            except Exception as error:
                logger.error(
                    f"Unexpected error for {school_id} (Attempt {attempt_number + 1}): {type(error).__name__}: {error}.",
                    exc_info=True
                )
                if attempt_number < self.config.max_retries:
                    await asyncio.sleep(self.config.backoff_factor ** attempt_number)
                else:
                    logger.error(f"Unexpected error persists for {school_id} after {self.config.max_retries + 1} attempts.")
                    return False, None, {"error_type": "Exception", "message": str(error)}
        logger.error(f"All retry attempts failed for {school_id}.")
        return False, None, None

    async def process_school_file(
        self,
        session: aiohttp.ClientSession,
        markdown_file_path: Path,
        rate_limiter: AsyncLimiter,
        semaphore: asyncio.Semaphore,
    ) -> bool:
        """Process a single school markdown file: read content, call AI API, and save results.

        Args:
            session: The aiohttp client session.
            markdown_file_path: Path to the input markdown file for a school.
            rate_limiter: An AsyncLimiter instance for rate control.
            semaphore: An asyncio.Semaphore to limit concurrent operations.

        Returns:
            True if processing was successful, False otherwise.
        """
        school_id = markdown_file_path.stem
        expected_output_md = self.markdown_output_dir / f"{school_id}{AI_PROCESSED_FILENAME_SUFFIX}"
        if expected_output_md.exists():
            logger.info(f"Output already exists for {school_id}, skipping AI processing.")
            return True
        async with semaphore:
            try:
                with markdown_file_path.open('r', encoding='utf-8') as markdown_file:
                    markdown_content = markdown_file.read()
                payload = self.create_ai_payload(markdown_content)
                success, ai_description, raw_response_json = await self.call_openai_api(
                    session, payload, school_id, rate_limiter
                )
                if success and ai_description:
                    self._save_ai_description(expected_output_md, ai_description)
                    if raw_response_json:
                        self._save_json_response(
                            self.json_output_dir / f"{school_id}{AI_RAW_RESPONSE_FILENAME_SUFFIX}",
                            raw_response_json
                        )
                    logger.info(f"Successfully processed and saved AI description for: {school_id}")
                    return True
                logger.error(f"Failed to get a valid AI description for: {school_id}")
                if raw_response_json:
                    self._save_json_response(
                        self.json_output_dir / f"{school_id}{AI_FAILED_RESPONSE_FILENAME_SUFFIX}",
                        raw_response_json
                    )
                    logger.info(f"Saved failed response JSON for {school_id}")
                return False
            except Exception as error:
                logger.error(
                    f"Error processing file {markdown_file_path.name} for school {school_id}: {error}",
                    exc_info=True
                )
                return False

    def _save_ai_description(self, output_path: Path, content: str) -> None:
        """Save the cleaned AI-generated markdown to file.

        Args:
            output_path: Path to save the markdown file.
            content: Markdown content to write.
        """
        with output_path.open("w", encoding="utf-8") as output_file:
            output_file.write(content)

    def _save_json_response(self, output_path: Path, response_json: dict) -> None:
        """Save the raw or failed AI JSON response to file.

        Args:
            output_path: Path to save the JSON file.
            response_json: JSON data to write.
        """
        with output_path.open("w", encoding="utf-8") as json_file:
            json.dump(response_json, json_file, ensure_ascii=False, indent=2)

    async def process_all_files(self, limit: Optional[int] = None) -> Dict[str, int]:
        """Process all markdown files in the input directory asynchronously.

        Args:
            limit: Optional maximum number of new files to process.

        Returns:
            Dictionary containing statistics about the processing run.
        """
        markdown_files: List[Path] = sorted(list(self.input_dir.glob("*.md")))
        if not markdown_files:
            logger.warning(f"No markdown files found in input directory: {self.input_dir.resolve()}")
            return self._build_stats_dict(0, 0, 0, 0, 0)
        skipped_count, files_to_process = self._filter_already_processed_files(markdown_files)
        if limit is not None and limit > 0 and len(files_to_process) > limit:
            logger.info(f"Limiting processing to the first {limit} new files out of {len(files_to_process)}.")
            files_to_process = files_to_process[:limit]
        if not files_to_process:
            logger.info("No new files require AI processing.")
            return self._build_stats_dict(len(markdown_files), skipped_count, 0, 0, 0)
        logger.info(f"Attempting to process {len(files_to_process)} new markdown files with AI.")
        rate_limiter = AsyncLimiter(self.config.target_rpm, 60)
        semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        connector = aiohttp.TCPConnector(
            force_close=True,
            limit=self.config.max_concurrent_requests
        )
        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                tasks = [
                    self.process_school_file(session, markdown_file, rate_limiter, semaphore)
                    for markdown_file in files_to_process
                ]
                results = await tqdm_asyncio.gather(*tasks, desc="Processing schools with AI")
            # Explicitly close the connector after the session context
            await connector.close()
            logger.info("aiohttp TCPConnector closed cleanly after all processing.")
            # Give the event loop a moment to finish closing connections
            await asyncio.sleep(0.1)
        except Exception as error:
            logger.error(f"Error during aiohttp session or connector shutdown: {error}", exc_info=True)
            raise
        successful_count = sum(1 for result in results if result is True)
        failed_count = len(files_to_process) - successful_count
        stats = self._build_stats_dict(
            len(markdown_files),
            skipped_count,
            len(files_to_process),
            successful_count,
            failed_count
        )
        logger.info(
            f"AI Processing completed: {successful_count} successful, {failed_count} failed "
            f"out of {len(files_to_process)} attempted."
        )
        return stats

    def _filter_already_processed_files(self, markdown_files: List[Path]) -> Tuple[int, List[Path]]:
        """Filter out already processed files.

        Args:
            markdown_files: List of markdown file paths.

        Returns:
            Tuple of (skipped_count, files_to_process).
        """
        skipped_count = 0
        files_to_process = []
        for markdown_file in markdown_files:
            school_id = markdown_file.stem
            expected_output_md = self.markdown_output_dir / f"{school_id}{AI_PROCESSED_FILENAME_SUFFIX}"
            if expected_output_md.exists():
                skipped_count += 1
            else:
                files_to_process.append(markdown_file)
        logger.info(
            f"Found {len(markdown_files)} total files in input directory. "
            f"{skipped_count} already processed. {len(files_to_process)} new files to process."
        )
        return skipped_count, files_to_process

    def _build_stats_dict(
        self,
        total_files: int,
        skipped: int,
        attempted: int,
        successful: int,
        failed: int
    ) -> Dict[str, int]:
        """Build a statistics dictionary for the processing run."""
        return {
            "total_files_in_input_dir": total_files,
            "skipped_already_processed": skipped,
            "attempted_to_process": attempted,
            "successful_ai_processing": successful,
            "failed_ai_processing": failed
        }


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments for the AI processor, including language and log level.

    Returns:
        Parsed arguments namespace.
    """
    import os

    parser = argparse.ArgumentParser(
        description="Process school description markdown files through an AI API."
    )
    parser.add_argument(
        "-l", "--limit",
        type=int,
        help="Limit the number of new school files to process (default: process all new files).",
        default=None
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        help="Input directory containing markdown files generated from CSV.",
        default=str(DEFAULT_INPUT_MARKDOWN_DIR)
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Base output directory for AI-processed files and raw responses.",
        default=str(DEFAULT_OUTPUT_BASE_DIR)
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
    return parser.parse_args()


def log_processing_summary(stats: Dict[str, int], markdown_output_dir: Path, json_output_dir: Path) -> None:
    """Log a summary of the AI processing run.

    Args:
        stats: Dictionary of processing statistics.
        markdown_output_dir: Directory where AI markdown files are saved.
        json_output_dir: Directory where raw JSON responses are saved.
    """
    logger.info("=" * 60)
    logger.info("AI PROCESSING SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total files in input directory: {stats.get('total_files_in_input_dir', 'N/A')}")
    logger.info(f"Skipped (already processed): {stats.get('skipped_already_processed', 'N/A')}")
    logger.info(f"Attempted to process: {stats.get('attempted_to_process', 'N/A')}")
    logger.info(f"Successfully processed by AI: {stats.get('successful_ai_processing', 'N/A')}")
    logger.info(f"Failed AI processing: {stats.get('failed_ai_processing', 'N/A')}")
    logger.info(f"Markdown output directory: {markdown_output_dir.resolve()}")
    logger.info(f"JSON responses directory: {json_output_dir.resolve()}")
    logger.info("=" * 60)


def main() -> None:
    """Main function to parse arguments and run the AI processor."""
    args = parse_arguments()
    # Reconfigure logging to use the requested log level
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(LOG_DIR / LOG_FILENAME_AI_PROCESSOR, mode='a'),
            logging.StreamHandler()
        ]
    )
    logger.info("="*50)
    logger.info("Starting Program 2: AI Processor")
    logger.info("="*50)
    # Language argument is accepted for future-proofing; not used in this script
    try:
        config = OpenAIConfig()
        processor = SchoolDescriptionProcessor(
            config=config,
            input_dir=Path(args.input),
            output_dir_base=Path(args.output)
        )
        stats = asyncio.run(processor.process_all_files(args.limit))
        log_processing_summary(stats, processor.markdown_output_dir, processor.json_output_dir)
    except KeyboardInterrupt:
        logger.warning("Processing interrupted by user.")
    except ValueError as error:
        logger.error(f"Configuration error: {error}")
    except Exception as error:
        logger.error(f"An unexpected error occurred in main: {type(error).__name__}: {error}", exc_info=True)


if __name__ == "__main__":
    main()