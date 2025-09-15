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
    def __init__(self, config: Any) -> None:
        self.config = config

    async def process_content(self, session: aiohttp.ClientSession, payload: dict[str, Any]):
        if not getattr(self.config, "gpt4o_endpoint", ""):
            return False, None, {"error_type": "ConfigurationError", "message": "OpenAI endpoint not set."}
        headers = {"Content-Type": "application/json", "api-key": str(self.config.api_key)}
        for attempt in range(getattr(self.config, "max_retries", 3) + 1):
            try:
                async with session.post(self.config.gpt4o_endpoint, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=getattr(self.config, "request_timeout", 300))) as response:
                    status = response.status
                    text = await response.text()
                    if status == 200:
                        try:
                            data = json.loads(text)
                            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                            if not content:
                                if attempt < getattr(self.config, "max_retries", 3):
                                    await asyncio.sleep(getattr(self.config, "backoff_factor", 2.0) ** attempt)
                                    continue
                                return False, None, data
                            if content.startswith("```"):
                                content = content.strip("`\n ")
                            return True, content, data
                        except json.JSONDecodeError:
                            return False, None, {"raw_response_text": text}
                    elif status == 429:
                        await asyncio.sleep(getattr(self.config, "retry_sleep_on_429", 60) * (attempt + 1))
                    else:
                        if attempt < getattr(self.config, "max_retries", 3):
                            await asyncio.sleep(getattr(self.config, "backoff_factor", 2.0) ** attempt)
                            continue
                        return False, None, {"status_code": status, "error_body": text}
            except aiohttp.ClientError as e:
                if attempt < getattr(self.config, "max_retries", 3):
                    await asyncio.sleep(getattr(self.config, "backoff_factor", 2.0) ** attempt)
                    continue
                return False, None, {"error_type": "ClientError", "message": str(e)}
            except TimeoutError:
                if attempt < getattr(self.config, "max_retries", 3):
                    await asyncio.sleep(getattr(self.config, "backoff_factor", 2.0) ** attempt)
                    continue
                return False, None, {"error_type": "TimeoutError"}
        return False, None, None

