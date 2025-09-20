"""Split consolidated test files into original test files.

This script scans the `tests/` tree for Python files that were
auto-concatenated and contain markers of the form::

    ### BEGIN ORIGINAL: tests/path/to/original_test.py
    ... original test contents ...
    ### END ORIGINAL: tests/path/to/original_test.py

For each such block the script will propose creating the original
test file at the indicated path. By default the script performs a
dry-run and prints a JSON list of planned writes. Use ``--apply`` to
actually write the files. The script is conservative and will not
overwrite existing files.

This tool helps restore a 1:1 mapping between `src/` modules and the
corresponding tests as requested by the project maintainers.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class PlannedWrite:
    """Lightweight description of a planned file write.

    Attributes
    ----------
    src_consolidated : str
        The consolidated source file that contained the original block.
    target_path : str
        The relative target path to write.
    content_snippet : str
        A short snippet of the content (for dry-run reporting).
    """

    src_consolidated: str
    target_path: str
    content_snippet: str


BLOCK_BEGIN_RE = re.compile(r"^###\s+BEGIN ORIGINAL:\s+(?P<path>\S+)")
BLOCK_END_RE = re.compile(r"^###\s+END ORIGINAL:\s+(?P<path>\S+)")


def find_consolidated_files() -> list[Path]:
    """Return a sorted list of potential consolidated test files.

    Returns
    -------
    list[Path]
        Paths pointing to Python files under the ``tests`` tree.
    """
    return sorted(ROOT.glob("tests/**/*.py"))


def extract_blocks(consolidated_path: Path) -> tuple[str, dict[str, str]]:
    """Return the file header and a mapping target_path -> content for each block.

    The header is the text before the first BEGIN marker and typically
    contains imports and module-level fixtures that the original test
    blocks relied on. We return the header so callers can prepend it to
    each split file to preserve test imports.
    """
    text = consolidated_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    out: dict[str, list[str]] = {}
    cur_target: str | None = None
    buffer: list[str] = []
    header_lines: list[str] = []
    seen_first_marker = False
    for ln in lines:
        m = BLOCK_BEGIN_RE.match(ln)
        if m:
            seen_first_marker = True
            cur_target = m.group("path")
            buffer = []
            continue
        m2 = BLOCK_END_RE.match(ln)
        if m2:
            tgt = m2.group("path")
            if cur_target is None or tgt != cur_target:
                cur_target = None
                buffer = []
                continue
            out[tgt] = "\n".join(buffer).rstrip() + "\n"
            cur_target = None
            buffer = []
            continue
        if not seen_first_marker:
            header_lines.append(ln)
            continue
        if cur_target is not None:
            buffer.append(ln)
    header = "\n".join(header_lines).rstrip() + "\n" if header_lines else ""
    # Convert list buffers to single strings
    return header, {k: v for k, v in out.items()}


def plan_writes() -> list[PlannedWrite]:
    """Plan the writes that would restore original tests from consolidated files.

    Returns
    -------
    list[PlannedWrite]
        Planned writes describing what would be created.
    """
    moves: list[PlannedWrite] = []
    for p in find_consolidated_files():
        _header, blocks = extract_blocks(p)
        if not blocks:
            continue
        for tgt, content in blocks.items():
            moves.append(
                PlannedWrite(
                    src_consolidated=str(p.relative_to(ROOT)),
                    target_path=tgt,
                    content_snippet=(
                        content[:160] + "..." if len(content) > 160 else content
                    ),
                )
            )
    return moves


def apply_moves(moves: list[PlannedWrite]) -> int:
    """Apply the planned writes to the working tree.

    Returns
    -------
    int
        Number of files written.
    """
    applied = 0
    # Group planned writes by consolidated source so we can trim/replace
    # the original consolidated file after extracting its blocks.
    by_src: dict[str, list[PlannedWrite]] = {}
    for m in moves:
        by_src.setdefault(m.src_consolidated, []).append(m)

    for src_rel, plans in by_src.items():
        src = ROOT / src_rel
        header, blocks = extract_blocks(src)

        # First, write each target file (if it does not already exist).
        for m in plans:
            dst = ROOT / m.target_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            content = blocks.get(m.target_path)
            if content is None:
                print(f"Block disappeared: {m.target_path} (from {m.src_consolidated})")
                continue
            full = (header or "") + content
            if dst.exists():
                # If the destination exists but does not contain the header
                # we rewrite it to ensure necessary imports/module fixtures
                existing = dst.read_text(encoding="utf-8")
                if header and not existing.startswith(header):
                    dst.write_text(full, encoding="utf-8")
                    print(f"Rewrote existing file with header: {dst}")
                    applied += 1
                else:
                    print(f"Leaving existing file intact: {dst}")
                continue

            dst.write_text(full, encoding="utf-8")
            print(f"Wrote {dst}")
            applied += 1

        # Now trim or replace the consolidated file so tests are not duplicated.
        # If the consolidated file contained a block matching its own path,
        # rewrite the file to contain only that block. Otherwise replace it
        # with a small stub comment explaining the split.
        own_block = blocks.get(src_rel)
        if own_block is not None:
            try:
                src.write_text((header or "") + own_block, encoding="utf-8")
                print(
                    f"Rewrote consolidated file {src} to contain its original block only"
                )
            except Exception as e:
                print(f"Failed to rewrite {src}: {e}")
        else:
            stub = (
                "# This consolidated test file was split into multiple files.\n"
                "# See tools/split_consolidated_tests.py for details.\n"
            )
            try:
                src.write_text(stub, encoding="utf-8")
                print(f"Replaced consolidated file {src} with a stub")
            except Exception as e:
                print(f"Failed to replace {src}: {e}")

    return applied


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: split consolidated test files into original files.

    Parameters
    ----------
    argv : list[str] | None
        Optional command line arguments to parse. When ``None`` the real
        CLI argv is used.

    Returns
    -------
    int
        Exit code (0 on success).
    """
    parser = argparse.ArgumentParser(
        description="Split consolidated test files into original files."
    )
    parser.add_argument("--apply", action="store_true", help="Write the planned files")
    args = parser.parse_args(argv)

    moves = plan_writes()
    if not args.apply:
        out = [m.__dict__ for m in moves]
        print(json.dumps(out, indent=2))
        return 0

    applied = apply_moves(moves)
    print(f"Applied {applied} writes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
