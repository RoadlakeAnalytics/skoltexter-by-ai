"""AI API client wrapper.

This module exposes a single class `AIAPIClient` that accepts an
`OpenAIConfig`-like object and provides a `process_content` coroutine that
takes a string and returns an AI-processed string. It contains only the
networking logic and no file I/O.
"""

import asyncio
import json
import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class AIAPIClient:
    """Client wrapper that sends payloads to the configured AI endpoint.

    The class encapsulates retry/backoff and basic response parsing so the
    higher-level processor can focus on orchestration.
    """

    def __init__(self, config: Any) -> None:
        self.config = config

    async def process_content(
        self, session: aiohttp.ClientSession, payload: dict[str, Any]
    ) -> tuple[bool, str | None, dict[str, Any] | None]:
        """Send the payload to the AI endpoint and return parsed result.

        The method is resilient to a number of failure modes:
        - Returns a configuration error if no endpoint is configured.
        - Handles HTTP 200 responses with empty or missing `choices`.
        - Retries on transient errors according to `max_retries` and
          `backoff_factor` config values.

        Parameters
        ----------
        session : aiohttp.ClientSession
            An aiohttp session or a test-double that implements `post`.
        payload : dict[str, Any]
            The JSON payload to post to the AI endpoint.

        Returns
        -------
        tuple[bool, str | None, dict[str, Any] | None]
            A tuple `(ok, cleaned_content, raw_response)` where `ok` is True
            on success, `cleaned_content` is the extracted text, and
            `raw_response` is the parsed JSON response when available.
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

        headers = {
            "Content-Type": "application/json",
            "api-key": str(self.config.api_key),
        }
        max_retries = getattr(self.config, "max_retries", 3)
        backoff = getattr(self.config, "backoff_factor", 2.0)

        for attempt in range(max_retries + 1):
            try:
                async with session.post(
                    self.config.gpt4o_endpoint,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(
                        total=getattr(self.config, "request_timeout", 300)
                    ),
                ) as response:
                    status = response.status
                    text = await response.text()

                    if status == 200:
                        try:
                            data = json.loads(text)
                        except json.JSONDecodeError:
                            return False, None, {"raw_response_text": text}

                        choices = (
                            data.get("choices", [])
                            if isinstance(data.get("choices", []), list)
                            else []
                        )
                        if not choices:
                            # No choices: retry if allowed, otherwise return raw data
                            if attempt < max_retries:
                                await asyncio.sleep(backoff**attempt)
                                continue
                            return False, None, data

                        # Safely extract message content
                        content = (
                            choices[0].get("message", {}).get("content", "")
                            if isinstance(choices[0], dict)
                            else ""
                        )
                        if not content:
                            if attempt < max_retries:
                                await asyncio.sleep(backoff**attempt)
                                continue
                            return False, None, data

                        # Strip common fenced-code wrappers
                        if isinstance(content, str) and content.startswith("```"):
                            import re

                            fence_pattern = re.compile(
                                r"^\s*```(?:[a-zA-Z0-9]+\s*\n)?(.*?)\n?```\s*$",
                                re.DOTALL | re.IGNORECASE,
                            )
                            m = fence_pattern.match(content.strip())
                            if m:
                                content = m.group(1).strip()
                            else:
                                content = content.strip("`\n ")

                        return True, content, data

                    if status == 429:
                        # Respect retry-after/backoff for rate limits
                        await asyncio.sleep(
                            getattr(self.config, "retry_sleep_on_429", 60)
                            * (attempt + 1)
                        )
                        continue

                    # Other HTTP errors
                    if attempt < max_retries:
                        await asyncio.sleep(backoff**attempt)
                        continue
                    return False, None, {"status_code": status, "error_body": text}

            except aiohttp.ClientError as e:
                if attempt < max_retries:
                    await asyncio.sleep(backoff**attempt)
                    continue
                return False, None, {"error_type": "ClientError", "message": str(e)}
            except TimeoutError:
                if attempt < max_retries:
                    await asyncio.sleep(backoff**attempt)
                    continue
                return False, None, {"error_type": "TimeoutError"}
            except Exception as err:
                # Unexpected exceptions: retry if possible, otherwise surface
                # a generic 'Exception' error_type so tests have a stable
                # discriminator.
                if attempt < max_retries:
                    await asyncio.sleep(backoff**attempt)
                    continue
                return False, None, {"error_type": "Exception", "message": str(err)}

        return False, None, None
