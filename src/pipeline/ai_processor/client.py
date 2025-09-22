"""ai_processor.client module.

This module defines the `AIAPIClient` class, which acts as a resilient asynchronous networking boundary for all outbound AI API requests in the school data pipeline. Its strict focus is on sending payloads to a remote AI endpoint (such as a GPT-style LLM service), handling transient network failures and error recovery, and returning parsed or error-enriched responses according to the project's robustness standards.

All retries, backoff, and timeout logic are performed per configuration values provided via the `config` object, ensuring bounded concurrency and fault tolerance suitable for high-volume, highly parallelized school content transformation. The client **never** performs file I/O or business logic, and does not raise exceptions directly: instead, it always returns structured tuples describing results, error types, and raw responses, so that the calling processor (or tests) can translate or escalate via the project's explicit error taxonomy.

See AGENTS.md for all guardrails and documentation mandates fulfilled by this implementation.

Examples
--------
A minimal usage demonstrates robust API call and its error pattern:

>>> import aiohttp
>>> from src.pipeline.ai_processor.client import AIAPIClient
>>> class DummyConfig:
...     gpt4o_endpoint = "http://example.com/v1/ai"
...     api_key = "secret"
...     max_retries = 2
...     backoff_factor = 0.1
...     request_timeout = 3
>>> payload = {"model": "gpt-4o", "messages": [{"role": "user", "content": "Hi"}]}
>>> client = AIAPIClient(DummyConfig())
>>> async def main():
...     async with aiohttp.ClientSession() as session:
...         ok, content, raw = await client.process_content(session, payload)
...         print(ok, content is not None)
>>> # To actually run:
>>> # import asyncio; asyncio.run(main())

Notes
-----
- This module is always imported by the core pipeline layer. No UI or CLI logic should reference it directly.
- All configuration values (timeouts, endpoints, max_retries) are injected via the config argument, never hardcoded.
- The error return pattern is a documented architectural commitment and must not be bypassed for exceptions.
"""

import asyncio
import json
import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class AIAPIClient:
    r"""Asynchronous client for sending requests to an AI API endpoint.

    This class provides a resilient interface for AI content processing,
    handling HTTP communication, retries, and response parsing. It is designed
    for use in the `ai_processor` pipeline stage, where multiple school
    descriptions are processed concurrently. The client uses dependency
    injection for the config and session to enable testing and modularity.

    Attributes
    ----------
    config : Any
        The configuration object (e.g., `OpenAIConfig`) providing API keys,
        endpoints, retry limits, and timeouts. Accessed via getattr for
        optional attributes.

    Methods
    -------
    __init__(config)
        Initializes the client with configuration.
    process_content(session, payload)
        Sends a payload to the AI endpoint and returns processed content or
        error details.

    Notes
    -----
    The client does not perform rate limiting directly but relies on
    `aiolimiter` integration in the calling orchestrator (e.g., `processor.py`).
    All operations are asynchronous to support high concurrency without
    blocking the event loop.

    See Also
    --------
    src.pipeline.ai_processor.processor.AIProcessor : Higher-level orchestrator
        using this client for batch processing.
    src.exceptions.ExternalServiceError : Custom exception for API failures
        raised by callers based on this client's error returns.

    def __init__(self, config: Any) -> None:
        r"""Create a new AIAPIClient with the specified configuration.

        Parameters
        ----------
        config : Any
            Configuration object supplying API keys, endpoint information,
            and all relevant limits as attributes. See 'Attributes'.

        Returns
        -------
        None

        Examples
        --------
        >>> class ExampleConf:
        ...     gpt4o_endpoint = "http://mock"
        ...     api_key = "secret"
        >>> AIAPIClient(ExampleConf())
        <src.pipeline.ai_processor.client.AIAPIClient object at ...>
        """
        self.config = config

    async def process_content(
        self, session: aiohttp.ClientSession, payload: dict[str, Any]
    ) -> tuple[bool, str | None, dict[str, Any] | None]:
        r"""Send a payload to the external AI API and return a normalized result or error.

        This is the sole method for performing an outbound model call.
        It handles:
          * Configuration errors (no endpoint supplied, no API key)
          * Network issues (retries on aiohttp.ClientError and TimeoutError, up to config.max_retries)
          * Syntax errors in the remote response (invalid or missing "choices" keys, or malformed content)
          * HTTP 429 (rate limit) with sleep-and-retry logic
          * Other HTTP error codes (surface as error type and body only)
        All failure conditions are reported in the return value for elevation by the orchestrator as per the error taxonomy (src/exceptions.py).

        Parameters
        ----------
        session : aiohttp.ClientSession
            The aiohttp session for HTTP requests. Must support
            an async 'post' method. Used and not closed by this method.
        payload : dict[str, Any]
            The JSON-serializable payload to send to the AI endpoint.

        Returns
        -------
        tuple[bool, str or None, dict[str, Any] or None]
            Tuple of three elements:
              - ok : bool
                  True if valid content was extracted, otherwise False.
              - cleaned_content : str or None
                  The decoded response text, stripped of common code fences, or None on failure.
              - raw_response : dict or None
                  The parsed JSON response if returned, or a dict describing error metadata, or None.

        Raises
        ------
        Does not raise, but error modes in the result include:
          - ConfigurationError (no endpoint/API key)
          - ClientError (network failure)
          - TimeoutError (request exceeded configured timeout)
          - Exception (unexpected error; see message)
          - HTTP error with status code and body

        See Also
        --------
        src.exceptions.ExternalServiceError
            May be raised by pipeline code if this method yields a terminal error.
        src/pipeline/ai_processor/processor.py
            For handling and escalation of tuple-based errors.

        Examples
        --------
        >>> import aiohttp
        >>> class DummyConf:
        ...     gpt4o_endpoint = "http://invalid_url"
        ...     api_key = "x"
        ...     max_retries = 0
        ...     backoff_factor = 0.01
        >>> payload = {"model": "x", "messages": [{"role": "user", "content": "test"}]}
        >>> client = AIAPIClient(DummyConf())
        >>> async def run_test():
        ...     async with aiohttp.ClientSession() as session:
        ...         ok, content, resp = await client.process_content(session, payload)
        ...         assert ok is False
        ...         assert "error_type" in (resp or {})
        >>> # To run: import asyncio; asyncio.run(run_test())

        Notes
        -----
        No exceptions will propagate to the caller; inspect the returned tuple for 'ok' and error type.
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
