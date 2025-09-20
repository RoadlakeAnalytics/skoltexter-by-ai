"""Add common imports to split test files that lack them.

Sometimes consolidated test files relied on a shared import header. When
tests are split the per-file imports may be missing which results in
lint errors such as `F821 undefined name 'pytest'`. This small utility
detects common patterns and prepends a safe, minimal header to files
that need it. It is conservative and only edits files when a likely
need is detected. Use `--apply` to perform the changes; default is
dry-run which prints the planned modifications as JSON.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

COMMON_HEADER = (
    "import asyncio\n"
    "import json\n"
    "from types import SimpleNamespace\n"
    "import aiohttp\n"
    "import pytest\n"
    "from pathlib import Path\n"
    "import logging\n"
    "import builtins\n"
    "import sys\n\n"
)


def should_add_header(text: str) -> bool:
    """Decide whether a test file likely needs the common header.

    The function looks for usages and markers commonly present in the
    consolidated header and returns True when the header should be
    prepended.
    """
    # If pytest is already imported, do nothing
    if "import pytest" in text or "from pytest" in text:
        return False
    # If the file references common names that typically came from the
    # consolidated header, consider adding the header.
    triggers = [
        "@pytest",
        "pytest.",
        "SimpleNamespace",
        "AIAPIClient",
        "aiohttp",
        "json.dumps",
        "json.loads",
        "asyncio.sleep",
    ]
    return any(t in text for t in triggers)


def find_targets() -> list[Path]:
    """Find test files that should be updated with the common header.

    Returns
    -------
    list[Path]
        Paths to candidate test files.
    """
    out: list[Path] = []
    for p in sorted(ROOT.glob("tests/**/*.py")):
        text = p.read_text(encoding="utf-8")
        if should_add_header(text):
            out.append(p)
    return out


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: optionally write the prepared headers to files.

    Parameters
    ----------
    argv : list[str] | None
        CLI argv to parse; when omitted the real CLI args are used.

    Returns
    -------
    int
        Exit code.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Add common test imports to split files"
    )
    parser.add_argument("--apply", action="store_true", help="Write changes")
    args = parser.parse_args(argv)

    targets = find_targets()
    planned = []
    for p in targets:
        planned.append(str(p))
    if not args.apply:
        print(json.dumps(planned, indent=2))
        return 0

    applied = 0
    for p in targets:
        text = p.read_text(encoding="utf-8")
        # If the file starts with a module docstring, insert the header
        # after the docstring so the docstring remains the first node.
        new_text = None
        stripped = text.lstrip()
        if stripped.startswith(('"""', "'''")):
            # Find the end of the docstring (first matching triple-quote)
            quote = stripped[:3]
            end_idx = stripped.find(quote, 3)
            if end_idx != -1:
                # end_idx is index of the closing quotes; compute offset
                prefix_len = len(text) - len(stripped)
                end_pos = prefix_len + end_idx + 3
                # include any following newline
                if end_pos < len(text) and text[end_pos] == "\n":
                    end_pos += 1
                new_text = text[:end_pos] + COMMON_HEADER + text[end_pos:]
        if new_text is None:
            new_text = COMMON_HEADER + text

        p.write_text(new_text, encoding="utf-8")
        print(f"Prepended header to {p}")
        applied += 1

    print(f"Applied {applied} changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
