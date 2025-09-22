"""Configuration and environment loader for the AI processor client.

This module provides OpenAIConfig, which loads, validates, and exposes
all configuration required by the AI pipeline for access to Azure OpenAI
and OpenAI Service endpoints.

Role in Architecture
--------------------
- Forms the boundary between process runtime/CI/developer environments and
  the pipeline's strongly-typed runtime config.
- Provides a single source of truth for API endpoint URIs, concurrency,
  retries/backoff, and rate limiting.
- No business or client logic: only configuration loading, structuring, and validation.

Examples
--------
>>> from src.pipeline.ai_processor.config import OpenAIConfig
>>> cfg = OpenAIConfig()
>>> assert isinstance(cfg.api_key, str)
>>> assert cfg.max_concurrent_requests > 0
"""

import os
from pathlib import Path

from dotenv import load_dotenv

import src.config as _project_config
from src.config import DEFAULT_API_VERSION, DEFAULT_DEPLOYMENT_NAME


class OpenAIConfig:
    r"""Configuration loader and validator for Azure/OpenAI service parameters.

    Loads and validates configuration from environment variables and an optional
    `.env` file, enforcing all requirements for the AI processing pipeline and
    client connection.

    Attributes
    ----------
    api_key : str | None
        The API key used to authenticate with OpenAI or Azure OpenAI service.
    endpoint_base : str | None
        The base endpoint URI for Azure OpenAI service (if applicable).
    deployment_name : str
        The configured deployment name for the large language model.
    api_version : str
        The API version used for Azure OpenAI endpoints.
    max_concurrent_requests : int
        Maximum parallel requests allowed by the client.
    target_rpm : int
        Target requests per minute limit for client rate control.
    max_retries : int
        Maximum allowed retries for transient request errors.
    backoff_factor : float
        Exponential backoff multiplier for retries.
    retry_sleep_on_429 : int
        Seconds to sleep on HTTP 429 (rate limit exceeded).
    temperature : float
        Sampling temperature for LLM queries.
    request_timeout : int
        Timeout (seconds) for individual requests.
    gpt4o_endpoint : str
        Complete endpoint URI to submit completion requests (may be empty).

    Notes
    -----
    Instantiate once at process start for deterministic, pre-validated config.
    No runtime mutation is intended.

    Examples
    --------
    >>> import os
    >>> os.environ["API_KEY"] = "unit-test"
    >>> from src.pipeline.ai_processor.config import OpenAIConfig
    >>> c = OpenAIConfig()
    >>> assert c.api_key == "unit-test"
    >>> assert isinstance(c.max_concurrent_requests, int)
    """

    def __init__(self) -> None:
        r"""Initialize an OpenAIConfig with strict validation of all required environment variables.

        Reads configuration from environment variables and a `.env` file at the
        project root if present, and validates presence of all required keys for
        either OpenAI or Azure OpenAI endpoints. Populates all attributes to be
        consumed by clients.

        Raises
        ------
        ValueError
            If no OpenAI/Azure API key is detected.
        ValueError
            If Azure credentials are set but the endpoint base is missing.

        Notes
        -----
        Loads `.env` using `dotenv` if present, for complete testability and
        reproducibility in CI/development.

        Examples
        --------
        >>> import os
        >>> os.environ["API_KEY"] = "demo"
        >>> from src.pipeline.ai_processor.config import OpenAIConfig
        >>> cfg = OpenAIConfig()
        >>> print(cfg.api_key)
        demo

        Failure (missing key):
        >>> import os
        >>> if "API_KEY" in os.environ: del os.environ["API_KEY"]  # doctest: +SKIP
        >>> from src.pipeline.ai_processor.config import OpenAIConfig
        >>> try:
        ...   OpenAIConfig()
        ... except ValueError as e:
        ...   assert "Missing API key" in str(e)
        """
        # Resolve project root dynamically from src.config so tests can
        # monkeypatch ``src.config.PROJECT_ROOT`` if needed. This removes
        # the previous fallback that inspected the legacy
        # ``src.program2_ai_processor`` module.
        env_root = Path(_project_config.PROJECT_ROOT)
        env_path = env_root / ".env"
        if env_path.exists():
            # Load project .env. When a `.env` file is present prefer its
            # values for configuration so local development and CI jobs can
            # provide a deterministic picture of configuration. Use
            # ``override=True`` so the file content is authoritative for
            # the duration of process startup and tests which create a
            # temporary `.env` file behave deterministically.
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
