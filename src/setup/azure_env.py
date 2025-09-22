"""Azure OpenAI Environment Configuration Helpers.

This module provides all logic for handling Azure OpenAI environment variable
configuration, prompting, and connectivity testing. It enables robust and
testable management of the `.env` file for API keys and endpoints, supports
interactive and non-interactive update flows, and provides connectivity
diagnostics for AI endpoints in a CI-friendly and modular fashion.

Architectural Boundaries
------------------------
- This file contains *no* business logic beyond environment configuration and diagnostics.
- All UI dependencies are injected or handled minimally for reliability in CI and test doubles.
- Configuration values are sourced via `src/config.py`, with no hard-coded values; tests may monkeypatch these.

Portfolio Context
-----------------
- Enables secure onboarding and connection checks for Azure OpenAI API usage.
- Supports interactive and automated flows (e.g., CI/cd, unit tests, local setup scripts).
- Decoupled from the launcher and orchestrator; usable both with rich UI or minimal console flows.
- All error handling conforms to the explicit taxonomy (`src/exceptions.py`).

References
----------
- AGENTS.md documentation standards (full NumPy-style docstring compliance).
- Azure OpenAI Python API documentation: https://learn.microsoft.com/en-us/azure/cognitive-services/openai/
- .env file format best practices.

Usage Examples
--------------
>>> from src.setup.azure_env import parse_env_file, find_missing_env_keys
>>> env = parse_env_file(Path(".env"))
>>> missing = find_missing_env_keys(env, REQUIRED_AZURE_KEYS)
>>> if missing:
...     prompt_and_update_env(missing, Path(".env"), env)
>>> success, msg = run_ai_connectivity_check_silent()
>>> print(success, msg)
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT

# Import ``aiohttp`` lazily inside the async helper so tests can inject a
# fake module into ``sys.modules['aiohttp']`` before the function runs.
aiohttp = None

# Default .env path (can be monkeypatched by tests)
ENV_PATH: Path = PROJECT_ROOT / ".env"


def parse_env_file(env_path: Path) -> dict[str, str]:
    r"""Parse a `.env` file of KEY="value" pairs into a dictionary.

    Reads and parses a `.env` file line by line, extracting key-value pairs in the format
    `KEY="value"`. Only lines matching this pattern are loaded. This function is used for
    robust bootstrapping of environment variable management for Azure OpenAI configuration.

    Parameters
    ----------
    env_path : Path
        Path to the `.env` file to read.

    Returns
    -------
    dict[str, str]
        Mapping of environment variable names to values. Returns an empty dictionary if the file does not exist
        or contains no valid pairs.

    Raises
    ------
    None.
        This function does not raise exceptions; malformed lines and missing files are handled gracefully.

    Notes
    -----
    - Ignores lines that cannot be parsed.
    - File absence is tolerated.
    - Relies on a regex suitable for upper-case variable convention.

    References
    ----------
    - AGENTS.md documentation standards.
    - .env best practices.

    Examples
    --------
    >>> from pathlib import Path
    >>> from src.setup.azure_env import parse_env_file
    >>> env = parse_env_file(Path(".env"))
    >>> sorted(env.keys())  # doctest: +SKIP
    ['AZURE_API_KEY', 'AZURE_ENDPOINT_BASE', ...]
    >>> parse_env_file(Path("nonexistent.env")) == {}
    True
    """
    env_dict: dict[str, str] = {}
    if not env_path.exists():
        return env_dict
    import re

    ENV_KEY_VALUE_PATTERN = re.compile(r'^\s*([A-Z0-9_]+)\s*=\s*["\']?(.*?)["\']?\s*$')
    with env_path.open("r", encoding="utf-8") as env_file:
        for line in env_file:
            match = ENV_KEY_VALUE_PATTERN.match(line)
            if match:
                key, value = match.groups()
                env_dict[key] = value
    return env_dict


REQUIRED_AZURE_KEYS: list[str] = [
    "AZURE_API_KEY",
    "AZURE_ENDPOINT_BASE",
    "GPT4O_DEPLOYMENT_NAME",
    "AZURE_API_VERSION",
]


def prompt_and_update_env(
    missing_keys: list[str], env_path: Path, existing: dict[str, str], ui: Any = None
) -> None:
    r"""Prompt for missing environment keys and write a new .env file.

    Prompts the user for each missing Azure/OpenAI environment variable, using either a provided UI
    object or a minimal fallback, updates the mapping, and rewrites the `.env` file in-place. Interactive
    and test-double flows are supported, ensuring no hard-coded UI dependency.

    Parameters
    ----------
    missing_keys : list[str]
        List of required environment variable names that must be prompted for.
    env_path : Path
        Path to the `.env` file where key/value pairs are stored.
    existing : dict[str, str]
        An existing mapping of keys to values, updated in-place.
    ui : Any, optional
        UI object providing `rprint`, `_`, and `ask_text`. If not provided, a minimal fallback is used.

    Returns
    -------
    None

    Raises
    ------
    None.
        Errors in reading or writing are surfaced as exceptions from Python's stdlib.

    Notes
    -----
    - Ensures minimal interactive fallback for tests/CI.
    - Augments the existing mapping without disturbing unrelated keys.

    Examples
    --------
    >>> import tempfile
    >>> from pathlib import Path
    >>> from src.setup.azure_env import prompt_and_update_env
    >>> env_path = Path(tempfile.gettempdir()) / "dummy.env"
    >>> keys = ["AZURE_API_KEY_TEST"]
    >>> env = {}
    >>> class DummyUI:
    ...     def rprint(self, *a, **k): pass
    ...     def _(self, text): return text
    ...     def ask_text(self, prompt): return "foo-key"
    >>> prompt_and_update_env(keys, env_path, env, ui=DummyUI())
    >>> env["AZURE_API_KEY_TEST"] == "foo-key"
    True
    >>> env_path.exists()
    True
    """
    import sys

    if ui is None:
        # Prefer the internal UI prompts module (so tests can monkeypatch
        # `src.setup.ui.prompts.ask_text`) before falling back to any legacy
        # top-level `setup_project` shim that may be present in sys.modules.
        try:
            from src.setup.ui import prompts as _prompts

            ui = _prompts
        except Exception:
            ui = sys.modules.get("setup_project")
            if ui is None:
                try:
                    from src.setup import ui as _ui

                    ui = _ui
                except Exception:
                    ui = None
    # Ensure we have required UI callables
    if not hasattr(ui, "rprint") or not hasattr(ui, "_") or not hasattr(ui, "ask_text"):
        from src.setup.console_helpers import rprint as _rprint
        from src.setup.i18n import _ as _t

        try:
            from src.setup.ui.prompts import ask_text as _ask
        except Exception:

            def _ask(prompt: str) -> str:  # type: ignore
                r"""Prompt for input using ``input()`` as fallback.

                Prompt is displayed directly to the user. Used only when
                richer UI is unavailable.
                
                Parameters
                ----------
                prompt : str
                    The prompt text.

                Returns
                -------
                str
                    Entered value.
                
                Examples
                --------
                >>> _ask("Enter value: ")  # doctest: +SKIP
                foo
                """
                return input(prompt)
 
        class _UI:
            r"""Minimal UI shim for test and CI fallback.

            Provides `rprint`, translation `_`, and `ask_text`. Used if richer prompts UI
            is unavailable (for CI, non-interactive mode, or test doubles).

            Notes
            -----
            - Avoids dependency on advanced prompt modules for reliability.
            - Exposes only minimal API for interactive use.
            
            Examples
            --------
            >>> ui = _UI()
            >>> hasattr(ui, "rprint")
            True
            >>> isinstance(ui.ask_text("Input: "), str)  # doctest: +SKIP
            True
            """
 
            rprint = staticmethod(_rprint)
            _ = staticmethod(_t)
            ask_text = staticmethod(_ask)
 
        ui = _UI()
 
    # Note: `_ask` is defined above in the import fallback; no further
    # redefinition is necessary.
 
    ui.rprint(f"\n{ui._('azure_env_intro')}\n{ui._('azure_env_storage')}")
    for key in missing_keys:
        prompt = ui._("azure_env_prompt").format(key=key)
        value = ""
        while not value:
            value = ui.ask_text(prompt)
        existing[key] = value
    updated_lines = []
    for key in missing_keys:
        updated_lines.append(f'{key}="{existing[key]}"\n')
    for key, value in existing.items():
        if key not in missing_keys:
            updated_lines.append(f'{key}="{value}"\n')
    with env_path.open("w", encoding="utf-8") as env_file:
        env_file.writelines(updated_lines)


def find_missing_env_keys(existing: dict[str, str], required: list[str]) -> list[str]:
    """Return a list of keys from ``required`` that are not present in ``existing``.

    Parameters
    ----------
    existing : dict[str, str]
        Existing environment mapping.
    required : list[str]
        List of required keys to check.

    Returns
    -------
    list[str]
        Keys that are missing from ``existing``.
    """
    return [key for key in required if not existing.get(key)]


def run_ai_connectivity_check_silent() -> tuple[bool, str]:
    """Perform a silent AI connectivity check against the configured endpoint.

    Returns
    -------
    tuple[bool, str]
        ``(True, 'Status: OK')`` on success, otherwise ``(False, <detail>)``
        describing the failure.
    """
    # Use the pipeline package configuration holder directly. Try importing
    # the symbol from the package root first (tests may patch that
    # location), otherwise fall back to the concrete config module.
    try:
        from src.pipeline.ai_processor import OpenAIConfig
    except Exception:
        from src.pipeline.ai_processor.config import OpenAIConfig

    cfg = OpenAIConfig()
    if not cfg.gpt4o_endpoint:
        return False, "Missing OpenAI endpoint configuration."
    user_prompt_en = (
        "This is a test. You must ONLY reply with the exact text 'Status: OK'. "
        "Are you ready? Reply 'Status: OK' if you are ready."
    )
    user_prompt_sv = (
        "Detta är ett test. Du måste ENDAST svara med exakt text 'Status: OK'. "
        "Är du redo? Svara 'Status: OK' om du är redo."
    )
    user_prompt = f"{user_prompt_sv}\n\n{user_prompt_en}"

    async def _check_once() -> tuple[bool, str]:
        """Perform a single asynchronous AI connectivity check.

        Returns
        -------
        tuple[bool, str]
            ``(True, 'Status: OK')`` on success, otherwise ``(False, detail)``.
        """
        try:
            import aiohttp
        except Exception:
            return False, "aiohttp not installed"
        try:
            headers = {"Content-Type": "application/json", "api-key": str(cfg.api_key)}
            payload = {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a concise assistant for connectivity tests.",
                    },
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 8,
                "temperature": 0.0,
            }
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=cfg.request_timeout)
            ) as session:
                async with session.post(
                    cfg.gpt4o_endpoint, json=payload, headers=headers
                ) as resp:
                    text = await resp.text()
                    if resp.status != 200:
                        return False, f"HTTP {resp.status}: {text[:200]}"
                    data = json.loads(text)
                    content = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                        .strip()
                    )
                    if content == "Status: OK":
                        return True, content
                    return False, f"Unexpected reply: {content[:200]}"
        except Exception as err:
            return False, f"{type(err).__name__}: {err}"

    return asyncio.run(_check_once())


def ensure_azure_openai_env(ui: Any = None) -> None:
    """Ensure required Azure/OpenAI environment variables exist.

    This helper reads the configured `.env` file (via :data:`ENV_PATH`),
    determines which keys are missing and, if any are absent, prompts the
    user (using `prompt_and_update_env`) to collect them and write an
    updated `.env` file.

    Parameters
    ----------
    ui : optional
        Optional UI object providing `rprint`, `_` and `ask_text`. If not
        provided a minimal console-backed UI is used.

    Returns
    -------
    None
    """
    env_path = globals().get("ENV_PATH", PROJECT_ROOT / ".env")
    existing = parse_env_file(env_path)
    missing = find_missing_env_keys(existing, REQUIRED_AZURE_KEYS)
    if missing:
        # Call the prompt helper with positional args to remain compatible
        # with test doubles that accept only the standard three parameters.
        prompt_and_update_env(missing, env_path, existing)
