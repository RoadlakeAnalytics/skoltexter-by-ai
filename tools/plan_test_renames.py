"""Plan safe, non-destructive test file renames to canonical locations.

This script analyses the repository and finds tests that import a single
`src/...` module (unambiguous). For those it proposes a canonical test
path under `tests/<path-after-src>/test_<module>_unit.py`. To avoid
basename collisions (pytest imports test modules by basename), the
script will prepend parent package names to the basename until it is
unique across the `tests/` tree.

The script only *plans* moves and prints a JSON list of mappings
``[{"from": "tests/old.py", "to": "tests/new.py"}, ...]``. It does
not modify files. Intended to be run locally or by CI during a
refactoring migration.
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


ROOT = Path(__file__).resolve().parents[1]


def find_src_files() -> List[Path]:
    return sorted(ROOT.glob("src/**/*.py"))


def find_test_files() -> List[Path]:
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
            p = m1.group(1).replace('.', os.sep) + '.py'
            if p in src_set:
                found.add(p)
        m2 = re.match(r"from\s+(src(?:\.[A-Za-z0-9_]+)+)\s+import\s+(.+)$", line)
        if m2:
            pkg = m2.group(1)
            parts = [p.strip().split(' as ')[0] for p in m2.group(2).split(',')]
            for part in parts:
                candidate = (pkg + '.' + part).replace('.', os.sep) + '.py'
                if candidate in src_set:
                    found.add(candidate)
            candidate_pkg = pkg.replace('.', os.sep) + '.py'
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
    # candidate start
    cand_parts = [module]
    # Try increasingly specific names
    for depth in range(1, len(parts) + 1):
        # take last `depth` parts as prefix (excluding the module stem)
        prefix_parts = parts[-(depth + 0):-0] if depth > 0 else []
        # However, more robust: walk from nearest parent outward
        prefix = "_".join(parts[-(depth + 1):-1]) if depth > 0 and len(parts) > 1 else ""
        if prefix:
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


def main() -> int:
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
    src_to_tests: Dict[str, List[str]] = defaultdict(list)  # type: ignore
    for t, imps in test_imports.items():
        for s in imps:
            src_to_tests[s].append(t)

    # existing basenames in tests (avoid collisions)
    used_basenames: Set[str] = {p.name for p in test_files}

    moves: List[Dict[str, str]] = []
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
        candidate_basename = unique_basename(src_path, used_basenames)
        canonical_dir = Path("tests") / rel_dir
        canonical_path = (canonical_dir / candidate_basename).as_posix()
        # Only plan move if current path differs from canonical
        if str(test_path) != canonical_path:
            moves.append({"from": str(test_path), "to": canonical_path})

    print(json.dumps(moves, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

