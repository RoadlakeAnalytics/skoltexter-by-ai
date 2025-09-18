"""OpenAI configuration loader.

Encapsulates environment loading and provides a small data holder used by
the client implementation.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.config import DEFAULT_API_VERSION, DEFAULT_DEPLOYMENT_NAME, PROJECT_ROOT


class OpenAIConfig:
    """Configuration holder that loads Azure/OpenAI settings from environment.

    The constructor reads a `.env` file if present and validates that required
    keys are available. It exposes configuration values as attributes used by
    the AI client and processor.
    """

    def __init__(self) -> None:
        env_root = PROJECT_ROOT
        pg_mod = sys.modules.get("src.program2_ai_processor")
        if pg_mod is not None and hasattr(pg_mod, "PROJECT_ROOT"):
            try:
                env_root = Path(pg_mod.PROJECT_ROOT)
            except Exception:
                env_root = PROJECT_ROOT
        env_path = env_root / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=True)
        self.api_key: str | None = os.getenv("API_KEY") or os.getenv("AZURE_API_KEY")
        azure_key = os.getenv("AZURE_API_KEY")
        self.endpoint_base: str | None = os.getenv("AZURE_ENDPOINT_BASE")
        self.deployment_name: str = os.getenv(
            "GPT4O_DEPLOYMENT_NAME", DEFAULT_DEPLOYMENT_NAME
        )
        self.api_version: str = os.getenv("AZURE_API_VERSION", DEFAULT_API_VERSION)
        self.max_concurrent_requests = int(os.getenv("MAX_CONCURRENT_REQUESTS", 250))
        self.target_rpm = int(os.getenv("TARGET_RPM", 10000))
        self.max_retries = int(os.getenv("MAX_RETRIES", 3))
        self.backoff_factor = float(os.getenv("BACKOFF_FACTOR", 2.0))
        self.retry_sleep_on_429 = int(os.getenv("RETRY_SLEEP_ON_429", 60))
        self.temperature = float(os.getenv("TEMPERATURE", 0.10))
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", 300))
        if not self.api_key:
            raise ValueError("Missing API key for OpenAI/Azure OpenAI configuration")
        if azure_key and not os.getenv("API_KEY") and not self.endpoint_base:
            raise ValueError(
                "Missing AZURE_ENDPOINT_BASE for Azure OpenAI configuration"
            )
        if self.endpoint_base:
            self.gpt4o_endpoint = f"{self.endpoint_base.rstrip('/')}/openai/deployments/{self.deployment_name}/chat/completions?api-version={self.api_version}"
        else:
            self.gpt4o_endpoint = ""
