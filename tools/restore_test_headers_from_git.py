"""Restore test file headers from consolidated files in git HEAD.

When consolidated test files were split the per-file imports may have
been lost. This utility reads the original consolidated files from the
git HEAD and reapplies their header (imports/docstring) to each
extracted block, overwriting the split files. It is intended as a
repair step after an automated split operation.

Use with caution; the script overwrites files in the working tree.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCK_BEGIN_RE = re.compile(r"^###\s+BEGIN ORIGINAL:\s+(?P<path>\S+)")
BLOCK_END_RE = re.compile(r"^###\s+END ORIGINAL:\s+(?P<path>\S+)")


def git_show(path: str) -> str:
    """Return file contents for `path` from git HEAD.

    Parameters
    ----------
    path : str
        Path inside the repository to show from HEAD.

    Returns
    -------
    str
        File contents as a string.
    """
    out = subprocess.check_output(["git", "show", f"HEAD:{path}"], text=True)
    return out


def parse_header_and_blocks_from_text(text: str) -> tuple[str, dict[str, str]]:
    """Extract the module header and named blocks from consolidated text.

    The consolidated file format contains markers of the form
    ``### BEGIN ORIGINAL: <path>`` / ``### END ORIGINAL: <path>``. This
    function returns the header content that appeared before the first
    block and a mapping of target paths to the extracted block content.
    """
    lines = text.splitlines()
    header_lines: list[str] = []
    cur: str | None = None
    buf: list[str] = []
    blocks: dict[str, str] = {}
    seen_first = False
    for ln in lines:
        m = BLOCK_BEGIN_RE.match(ln)
        if m:
            seen_first = True
            cur = m.group("path")
            buf = []
            continue
        m2 = BLOCK_END_RE.match(ln)
        if m2:
            tgt = m2.group("path")
            if cur is None or tgt != cur:
                cur = None
                buf = []
                continue
            blocks[tgt] = "\n".join(buf).rstrip() + "\n"
            cur = None
            buf = []
            continue
        if not seen_first:
            header_lines.append(ln)
            continue
        if cur is not None:
            buf.append(ln)
    header = "\n".join(header_lines).rstrip() + "\n" if header_lines else ""
    return header, blocks


def find_consolidated_in_head() -> list[str]:
    """Find consolidated test files in git HEAD that contain original blocks.

    Returns
    -------
    list[str]
        Sorted list of consolidated file paths that contain original blocks.
    """
    out = subprocess.check_output(
        ["git", "grep", "-n", "### BEGIN ORIGINAL", "HEAD"], text=True
    )
    paths = set()
    for line in out.splitlines():
        # git grep with a tree-ish prefix yields lines like
        # "HEAD:tests/...:lineno:...". Extract the path part.
        parts = line.split(":")
        if len(parts) >= 3 and parts[0] == "HEAD":
            path = parts[1]
        elif len(parts) >= 2:
            path = parts[0]
        else:
            continue
        paths.add(path)
    return sorted(paths)


def main() -> int:
    """CLI entrypoint: restore headers for consolidated tests from git HEAD.

    Returns
    -------
    int
        Exit code.
    """
    paths = find_consolidated_in_head()
    written = 0
    for p in paths:
        try:
            text = git_show(p)
        except subprocess.CalledProcessError:
            print(f"Could not read {p} from HEAD")
            continue
        header, blocks = parse_header_and_blocks_from_text(text)
        if not blocks:
            continue
        for tgt, content in blocks.items():
            dst = ROOT / tgt
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text((header or "") + content, encoding="utf-8")
            print(f"Restored header to {dst}")
            written += 1
        # For the consolidated file itself, if it had an own block, rewrite
        own = blocks.get(p)
        src_path = ROOT / p
        if own is not None and src_path.exists():
            src_path.write_text((header or "") + own, encoding="utf-8")
            print(f"Rewrote consolidated {src_path} to its own block")

    print(f"Restored headers for {written} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
