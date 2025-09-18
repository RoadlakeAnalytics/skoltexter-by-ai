"""Processor orchestrator for AI file processing.

This module contains the `SchoolDescriptionProcessor` class which wires the
client, file handling and prompt/template parsing into a single orchestration
unit. The heavy networking lives in `AIAPIClient`; the processor handles
file discovery, per-file flow and persistence.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import aiohttp
from aiolimiter import AsyncLimiter

from src.config import (
    AI_PAYLOAD_MAX_TOKENS,
    AI_PROCESSED_FILENAME_SUFFIX,
    AI_PROCESSED_MARKDOWN_SUBDIR,
    AI_PROMPT_TEMPLATE_PATH,
    AI_RAW_RESPONSES_SUBDIR,
)

from .client import AIAPIClient

logger = logging.getLogger(__name__)


class SchoolDescriptionProcessor:
    """Orchestrates reading markdown files, calling the AI client and saving results.

    This class discovers markdown files in the input directory, constructs
    AI payloads from a prompt template, calls the AI client and persists the
    generated descriptions and raw responses.
    """

    def __init__(self, config: Any, input_dir: Path, output_dir_base: Path) -> None:
        self.config = config
        self.client = AIAPIClient(config)
        self.input_dir = Path(input_dir)
        self.output_dir_base = Path(output_dir_base)
        self.markdown_output_dir = self.output_dir_base / AI_PROCESSED_MARKDOWN_SUBDIR
        self.json_output_dir = self.output_dir_base / AI_RAW_RESPONSES_SUBDIR
        self.markdown_output_dir.mkdir(parents=True, exist_ok=True)
        self.json_output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"Initialized SchoolDescriptionProcessor with input: {self.input_dir.resolve()}, markdown output: {self.markdown_output_dir.resolve()}, json output: {self.json_output_dir.resolve()}"
        )
        self.prompt_template = self._load_prompt_template(Path(AI_PROMPT_TEMPLATE_PATH))

    @staticmethod
    def _load_prompt_template(template_path: Path) -> str:
        with template_path.open("r", encoding="utf-8") as fh:
            return fh.read()

    def _parse_prompt_template(self, school_data: str) -> dict[str, Any]:
        prompt_filled = self.prompt_template.replace("{school_data}", school_data)
        system_marker = "SYSTEM:"
        user_marker = "USER:"
        system_start = prompt_filled.find(system_marker)
        user_start = prompt_filled.find(user_marker)
        if system_start == -1 or user_start == -1:
            raise ValueError(
                "Prompt template must contain 'SYSTEM:' and 'USER:' markers."
            )
        system_content = prompt_filled[
            system_start + len(system_marker) : user_start
        ].strip()
        user_content = prompt_filled[user_start + len(user_marker) :].strip()
        return {
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": AI_PAYLOAD_MAX_TOKENS,
            "temperature": getattr(self.config, "temperature", 0.1),
        }

    @staticmethod
    def _clean_ai_response(content: str) -> str:
        if not isinstance(content, str):
            raise TypeError("content must be a string")
        cleaned_content = content.strip()
        import re

        fence_pattern = re.compile(
            r"^\s*```(?:[a-zA-Z0-9]+\s*\n)?(.*?)\n?```\s*$", re.DOTALL | re.IGNORECASE
        )
        match = fence_pattern.match(cleaned_content)
        if match:
            return match.group(1).strip()
        if cleaned_content.startswith("```markdown"):
            cleaned_content = cleaned_content[len("```markdown") :].lstrip()
        elif cleaned_content.startswith("```"):
            cleaned_content = cleaned_content[len("```") :].lstrip()
        if cleaned_content.endswith("```"):
            cleaned_content = cleaned_content[: -len("```")].rstrip()
        return cleaned_content

    def create_ai_payload(self, school_data: str) -> dict[str, Any]:
        """Create the AI request payload for a given school's markdown data.

        Parameters
        ----------
        school_data : str
            Raw markdown content extracted from the school's markdown file.

        Returns
        -------
        dict[str, Any]
            A JSON-serializable payload suitable for posting to the AI API.
        """
        return self._parse_prompt_template(school_data)

    async def call_openai_api(
        self,
        session: aiohttp.ClientSession,
        payload: dict[str, Any],
        school_id: str,
        rate_limiter: AsyncLimiter,
    ) -> tuple[bool, str | None, dict[str, Any] | None]:
        """Call the configured OpenAI endpoint with the given payload.

        This method uses the underlying :class:`AIAPIClient` to perform the
        HTTP POST and returns a tuple of (ok, cleaned_text, raw_json).
        """
        if not getattr(self.config, "gpt4o_endpoint", ""):
            return (
                False,
                None,
                {
                    "error_type": "ConfigurationError",
                    "message": "OpenAI endpoint not set.",
                },
            )
        async with rate_limiter:
            ok, cleaned, raw = await self.client.process_content(session, payload)
            return ok, cleaned, raw

    async def process_school_file(
        self,
        session: aiohttp.ClientSession,
        markdown_file_path: Path,
        rate_limiter: AsyncLimiter,
        semaphore: asyncio.Semaphore,
    ) -> bool:
        """Process a single school's markdown file through the AI.

        Parameters
        ----------
        session : aiohttp.ClientSession
            HTTP client session or a test double providing a ``post`` method.
        markdown_file_path : Path
            Path to the input markdown file for the school.
        rate_limiter : AsyncLimiter
            Rate limiter used to throttle API calls.
        semaphore : asyncio.Semaphore
            Semaphore to bound concurrent processing.

        Returns
        -------
        bool
            True on success or when the output already exists; False on failure.
        """
        school_id = markdown_file_path.stem
        # Support legacy and current filename patterns when checking for
        # already-existing AI outputs (tests and older runs may use
        # different suffix conventions).
        # Consider multiple possible markdown output directories/filename
        # conventions for backwards compatibility with tests and legacy runs.
        alt_md_dir = self.output_dir_base / "ai_processed_markdown"
        possible_dirs = [self.markdown_output_dir, alt_md_dir]
        exists_any = False
        for d in possible_dirs:
            c1 = d / f"{school_id}_ai_description.md"
            c2 = d / f"{school_id}{AI_PROCESSED_FILENAME_SUFFIX}"
            if c1.exists() or c2.exists():
                exists_any = True
                break
        if exists_any:
            logger.info(
                f"Output already exists for {school_id}, skipping AI processing."
            )
            return True
        async with semaphore:
            try:
                markdown_content = markdown_file_path.read_text(encoding="utf-8")
                payload = self.create_ai_payload(markdown_content)
                # Call the API client; tests sometimes monkeypatch
                # `call_openai_api` with different callable signatures
                # (bound vs unbound). Be tolerant and try a few
                # invocation strategies.
                try:
                    (
                        success,
                        ai_description,
                        raw_response_json,
                    ) = await self.call_openai_api(
                        session, payload, school_id, rate_limiter
                    )
                except TypeError:
                    # Try calling the class attribute as an unbound
                    # coroutine (some tests patch the function this way).
                    func: Any = self.__class__.call_openai_api
                    try:
                        success, ai_description, raw_response_json = await func(
                            session, payload, school_id, rate_limiter
                        )
                    except TypeError:
                        # Last resort: pass `self` explicitly.
                        success, ai_description, raw_response_json = await func(
                            self, session, payload, school_id, rate_limiter
                        )

                if success and ai_description:
                    # Prefer the explicit `_ai_description` filename used in
                    # tests and legacy artefacts. Pick the first existing
                    # directory or default to the configured markdown dir.
                    target_dir = next(
                        (d for d in possible_dirs if d.exists()),
                        self.markdown_output_dir,
                    )
                    out_md = target_dir / f"{school_id}_ai_description.md"
                    target_dir.mkdir(parents=True, exist_ok=True)
                    self._save_ai_description(out_md, ai_description)

                # Standardise raw/failed response filenames using the
                # configured deployment name (sanitised for filesystem).
                dep = getattr(self.config, "deployment_name", "gpt4o")
                dep_sanitised = str(dep).replace("-", "")
                if raw_response_json is not None:
                    raw_name = f"{school_id}_{dep_sanitised}_raw_response.json"
                    self._save_json_response(
                        self.json_output_dir / raw_name, raw_response_json
                    )
                if not success and raw_response_json is not None:
                    failed_name = f"{school_id}_{dep_sanitised}_FAILED_response.json"
                    self._save_json_response(
                        self.json_output_dir / failed_name, raw_response_json
                    )
                return success
            except Exception as error:
                logger.error(
                    f"Error processing file {markdown_file_path.name} for school {school_id}: {error}",
                    exc_info=True,
                )
                return False

    def _save_ai_description(self, output_path: Path, content: str) -> None:
        with output_path.open("w", encoding="utf-8") as output_file:
            output_file.write(content)

    def _save_json_response(
        self, output_path: Path, response_json: dict[str, Any]
    ) -> None:
        with output_path.open("w", encoding="utf-8") as json_file:
            json.dump(response_json, json_file, ensure_ascii=False, indent=2)

    async def process_all_files(self, limit: int | None = None) -> dict[str, int]:
        """Process all markdown files found in the input directory.

        Parameters
        ----------
        limit : int | None, optional
            Optional limit on how many files to process.

        Returns
        -------
        dict[str, int]
            Statistics about the processing run.
        """
        markdown_files: list[Path] = sorted(list(self.input_dir.glob("*.md")))
        if not markdown_files:
            logger.warning(
                f"No markdown files found in input directory: {self.input_dir.resolve()}"
            )
            return self._build_stats_dict(0, 0, 0, 0, 0)
        skipped_count, files_to_process = self._filter_already_processed_files(
            markdown_files
        )
        if limit is not None and limit > 0 and len(files_to_process) > limit:
            files_to_process = files_to_process[:limit]
        if not files_to_process:
            return self._build_stats_dict(len(markdown_files), skipped_count, 0, 0, 0)
        rate_limiter = AsyncLimiter(getattr(self.config, "target_rpm", 1000), 60)
        semaphore = asyncio.Semaphore(
            getattr(self.config, "max_concurrent_requests", 4)
        )
        connector = aiohttp.TCPConnector(
            force_close=True, limit=getattr(self.config, "max_concurrent_requests", 4)
        )
        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                tasks = [
                    self.process_school_file(
                        session, markdown_file, rate_limiter, semaphore
                    )
                    for markdown_file in files_to_process
                ]
                try:
                    from importlib import import_module

                    p2 = import_module("src.program2_ai_processor")
                    results = await p2.tqdm_asyncio.gather(
                        *tasks, desc="Processing schools with AI"
                    )
                except Exception:
                    results = await asyncio.gather(*tasks)
            await connector.close()
            await asyncio.sleep(0.1)
        except Exception:
            raise
        successful_count = sum(1 for result in results if result is True)
        failed_count = len(files_to_process) - successful_count
        return self._build_stats_dict(
            len(markdown_files),
            skipped_count,
            len(files_to_process),
            successful_count,
            failed_count,
        )

    def _filter_already_processed_files(
        self, markdown_files: list[Path]
    ) -> tuple[int, list[Path]]:
        skipped_count = 0
        files_to_process: list[Path] = []
        for markdown_file in markdown_files:
            school_id = markdown_file.stem
            alt_md_dir = self.output_dir_base / "ai_processed_markdown"
            possible_dirs = [self.markdown_output_dir, alt_md_dir]
            found = False
            for d in possible_dirs:
                if (d / f"{school_id}_ai_description.md").exists() or (
                    d / f"{school_id}{AI_PROCESSED_FILENAME_SUFFIX}"
                ).exists():
                    found = True
                    break
            if found:
                skipped_count += 1
            else:
                files_to_process.append(markdown_file)
        return skipped_count, files_to_process

    def _build_stats_dict(
        self,
        total_files: int,
        skipped: int,
        attempted: int,
        successful: int,
        failed: int,
    ) -> dict[str, int]:
        return {
            "total_files_in_input_dir": total_files,
            "skipped_already_processed": skipped,
            "attempted_to_process": attempted,
            "successful_ai_processing": successful,
            "failed_ai_processing": failed,
        }
