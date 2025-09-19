"""Plan and optionally apply safe test file renames.

This tool analyses the repository and finds tests that import a single
`src/...` module (unambiguous). For those it proposes a canonical test
path under `tests/<path-after-src>/test_<module>_unit.py`.

By default the script prints a JSON list of mappings ``[{"from": "...",
"to": "..."}, ...]`` without modifying the repository. Use ``--apply``
to actually perform the rename operations. The apply mode is conservative
and will skip operations where the destination already exists or the
source no longer exists.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set


ROOT = Path(__file__).resolve().parents[1]


def find_src_files() -> list[Path]:
    return sorted(ROOT.glob("src/**/*.py"))


def find_test_files() -> list[Path]:
    return sorted(ROOT.glob("tests/**/*.py"))


def parse_imported_srcs(test_path: Path, src_set: Set[str]) -> Set[str]:
    """Return set of src file paths (relative to repo root) imported by test.

    We look for `import src.xxx.yyy` and `from src.xxx.yyy import z` forms.
    """
    text = test_path.read_text(encoding="utf-8")
    found: Set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        m1 = re.match(r"import\s+(src(?:\.[A-Za-z0-9_]+)+)", line)
        if m1:
            p = m1.group(1).replace(".", os.sep) + ".py"
            if p in src_set:
                found.add(p)
        m2 = re.match(r"from\s+(src(?:\.[A-Za-z0-9_]+)+)\s+import\s+(.+)$", line)
        if m2:
            pkg = m2.group(1)
            parts = [p.strip().split(" as ")[0] for p in m2.group(2).split(",")]
            for part in parts:
                candidate = (pkg + "." + part).replace(".", os.sep) + ".py"
                if candidate in src_set:
                    found.add(candidate)
            candidate_pkg = pkg.replace(".", os.sep) + ".py"
            if candidate_pkg in src_set:
                found.add(candidate_pkg)
    return found


def unique_basename(module_path: Path, used_basenames: Set[str]) -> str:
    """Generate a unique test basename for a module by adding parents.

    Start with `test_<module>_unit.py`. If that basename collides, prepend
    parent directory names until unique.
    """
    parts = list(module_path.parts)
    module = module_path.stem
    # Try increasingly specific names
    for depth in range(0, len(parts)):
        if depth > 0 and len(parts) > 1:
            prefix = "_".join(parts[-(depth + 1) : -1])
            cand = f"test_{prefix}_{module}_unit.py"
        else:
            cand = f"test_{module}_unit.py"
        if cand not in used_basenames:
            used_basenames.add(cand)
            return cand
    # fallback: include full dotted path
    dotted = "_".join(module_path.with_suffix("").parts)
    cand = f"test_{dotted}_unit.py"
    used_basenames.add(cand)
    return cand


def compute_canonical_basenames(src_paths: list[Path]) -> Dict[str, str]:
    """Deterministically compute canonical basenames for all src modules.

    This function ensures uniqueness by disambiguating modules that share
    the same filename (stem) using parent directory names from nearest to
    farthest. Returns a mapping keyed by the src relative path string.
    """
    # Group by module stem
    by_stem: dict[str, list[Path]] = defaultdict(list)
    for p in src_paths:
        by_stem[p.stem].append(p)

    canonical: Dict[str, str] = {}
    used: Set[str] = set()

    for stem, paths in by_stem.items():
        if len(paths) == 1:
            cand = f"test_{stem}_unit.py"
            if cand in used:
                dotted = "_".join(paths[0].with_suffix("").parts)
                cand = f"test_{dotted}_unit.py"
            canonical[str(paths[0].relative_to(ROOT))] = cand
            used.add(cand)
            continue

        # Disambiguate a group of paths sharing the same stem
        parent_parts = {p: list(p.parts[1:-1]) for p in paths}
        depth_map = {p: 0 for p in paths}

        def make_candidate(p: Path, depth: int) -> str:
            parts = parent_parts[p]
            if depth <= 0 or not parts:
                return f"test_{p.stem}_unit.py"
            prefix = "_".join(parts[-depth:])
            return f"test_{prefix}_{p.stem}_unit.py"

        # Iteratively increase depth until all candidates are unique
        while True:
            cands = [make_candidate(p, depth_map[p]) for p in paths]
            counts = defaultdict(int)
            for c in cands:
                counts[c] += 1
            dup = any(v > 1 for v in counts.values())
            coll = any(c in used for c in cands)
            if not dup and not coll:
                for p, c in zip(paths, cands):
                    canonical[str(p.relative_to(ROOT))] = c
                    used.add(c)
                break

            # increase depth for ambiguous candidates
            for i, p in enumerate(paths):
                c = cands[i]
                if counts[c] > 1 or c in used:
                    if depth_map[p] < len(parent_parts[p]):
                        depth_map[p] += 1
                    else:
                        dotted = "_".join(p.with_suffix("").parts)
                        cand = f"test_{dotted}_unit.py"
                        if cand in used:
                            cand = f"test_{dotted}_{i}_unit.py"
                        canonical[str(p.relative_to(ROOT))] = cand
                        used.add(cand)
    return canonical


def _compute_moves() -> list[Dict[str, str]]:
    src_files = find_src_files()
    test_files = find_test_files()
    src_set = {str(p.relative_to(ROOT)) for p in src_files}

    # map test -> imported srcs
    test_imports: Dict[str, Set[str]] = {}
    for t in test_files:
        # skip conftest and __init__ files
        if t.name in ("conftest.py", "__init__.py"):
            continue
        imps = parse_imported_srcs(t, src_set)
        if imps:
            test_imports[str(t.relative_to(ROOT))] = imps

    # invert mapping to src -> tests that import it
    src_to_tests: Dict[str, list[str]] = defaultdict(list)  # type: ignore
    for t, imps in test_imports.items():
        for s in imps:
            src_to_tests[s].append(t)

    # Compute deterministic canonical basenames for all src modules
    canonical_map = compute_canonical_basenames(src_files)

    # existing basenames in tests (avoid collisions)
    used_basenames: Set[str] = {p.name for p in test_files}

    moves: list[Dict[str, str]] = []
    for s, tests in src_to_tests.items():
        if len(tests) != 1:
            # ambiguous mapping; skip to be safe
            continue
        src_path = Path(s)
        test_path = Path(tests[0])
        # Only plan moves for tests that import exactly one src module
        # (unambiguous test-to-src relation). This prevents the same
        # test file from being moved into multiple canonical locations.
        if len(test_imports.get(str(test_path), set())) != 1:
            continue
        # canonical dir under tests/<path after src/>
        rel_dir = Path(*src_path.parts[1:-1])  # skip leading 'src' and module filename
        # ensure we include subfolders mirroring src
        # canonical_map is keyed by src-relative strings like 'src/.../mod.py'
        candidate_basename = canonical_map.get(s)
        if candidate_basename is None:
            # fallback to conservative unique basename
            candidate_basename = unique_basename(src_path, used_basenames)
        canonical_dir = Path("tests") / rel_dir
        canonical_path = (canonical_dir / candidate_basename).as_posix()
        # Only plan move if current path differs from canonical
        if str(test_path) != canonical_path:
            moves.append({"from": str(test_path), "to": canonical_path})

    return moves


def _apply_moves(moves: list[Dict[str, str]]) -> int:
    applied = 0
    for m in moves:
        src = Path(m["from"])
        dst = Path(m["to"])
        if not src.exists():
            print(f"Skipping move; source does not exist: {src}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            print(f"Skipping move; destination already exists: {dst}")
            continue
        src.rename(dst)
        print(f"Moved {src} -> {dst}")
        applied += 1
    return applied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Plan or apply deterministic test file renames to mirror src/ structure."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually perform the planned moves (default: dry-run).",
    )
    args = parser.parse_args(argv)

    moves = _compute_moves()
    if not args.apply:
        print(json.dumps(moves, indent=2))
        return 0

    applied = _apply_moves(moves)
    print(f"Applied {applied} moves")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

