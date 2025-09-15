"""Helpers for Azure OpenAI .env prompting and connectivity checks.

This module extracts .env parsing, prompting and the AI connectivity test
so the main entrypoint can stay compact.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

# Import ``aiohttp`` lazily inside the async helper so tests can inject a
# fake module into ``sys.modules['aiohttp']`` before the function runs.
aiohttp = None


def parse_env_file(env_path: Path) -> dict[str, str]:
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
    missing_keys: list[str], env_path: Path, existing: dict[str, str], ui=None
) -> None:
    """Prompt the user for missing env keys and write a new .env file."""
    import sys

    if ui is None:
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
                return input(prompt)

        class _UI:
            rprint = staticmethod(_rprint)
            _ = staticmethod(_t)
            ask_text = staticmethod(_ask)

        ui = _UI()

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
    return [key for key in required if not existing.get(key)]


def run_ai_connectivity_check_silent() -> tuple[bool, str]:
    from src.program2_ai_processor import OpenAIConfig

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

    async def _check_once():
        try:
            import aiohttp  # type: ignore
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
