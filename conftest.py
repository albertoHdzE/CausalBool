"""Root pytest configuration: import bootstrap, and manifest-driven collection.

AUDIT04-E. Two defects made this file necessary, and both were invisible for the
same reason -- nothing declared what the Python half of `tests/` was.

------------------------------------------------------------------------------
1. A CROSS-REPOSITORY sys.path LEAK IN THIS PROJECT'S OWN VENV
------------------------------------------------------------------------------
`venv/lib/python3.13/site-packages/deconv_lab_paths.pth` appends three source
trees belonging to OTHER repositories:

    /Users/alberto/Documents/projects/deconv-lab/src
    /Users/alberto/Documents/projects/deconv-lab/experiments
    /Users/alberto/Documents/projects/decon-fin/src

Measured rather than assumed, on 2026-09-07:

    foreign top-level importable names   83
    CausalBool src/ top-level names      14
    COLLISIONS                            1 of 14   -- `data`

That single collision is not harmless. `import data` inside this repository was
resolving to `decon-fin/src/data.py`, so
`tests/Nature/TSK-NATURE-LEV3-DATA-003-Test.py` and
`tests/Nature/TSK-NATURE-LEV3-PHASE4-Integration-Test.py` both died at collection
with `'data' is not a package`. Controlled check -- strip those two entries from
`sys.path` and rerun the same two files unchanged:

    with the foreign entries      1 error during collection (both files)
    without them                  3 passed

So the DEVELOPER MACHINE was the broken environment, not the code, and a clean
checkout would have passed where this one failed. That is the reverse of the
usual failure and it is why nobody suspected the venv.

The fix here is repo-local and reversible: put this repository's `src/` at the
FRONT of `sys.path`, so CausalBool's own packages win any name contest. The
`.pth` file belongs to a sibling project's setup and is NOT touched -- deleting
another project's configuration to fix ours would be the wrong direction, and it
is recorded in GOVERNANCE/VERIFICATION.md as an environment hazard instead.

Why `src` and not just the repo root: the 24 Python test files under `tests/`
each carry their own `sys.path.append(.../src)` and then import `integration.X`,
while `tests/analysis/` imports `src.description_lengths`. Both conventions are
live, so both roots must be importable, and only the `src` entry has to be first.

------------------------------------------------------------------------------
2. COLLECTION IS DECLARED, NOT DISCOVERED -- IN BOTH LANGUAGES
------------------------------------------------------------------------------
`tests/MUnit/MANIFEST.tsv` is the single owner of test membership. Until now it
covered only Wolfram files, so which Python files ran was decided by a glob in
`pytest.ini` -- exactly the discover-by-glob arrangement the manifest was created
to end, surviving in the other language.

`collect_ignore` below is therefore read FROM THE MANIFEST. A Python file
declared `quarantine` or `producer` is not collected; a file declared `test` is.
There is no second list to drift out of step with the first.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "tests" / "MUnit" / "MANIFEST.tsv"

# --- 1. import bootstrap -----------------------------------------------------
# `src` FIRST: it must outrank the foreign trees appended by the .pth file.
# The repo root stays importable too, for `from src.x import y`.
for _entry in (str(ROOT / "src"), str(ROOT)):
    while _entry in sys.path:
        sys.path.remove(_entry)
    sys.path.insert(0, _entry)


# --- 2. manifest-driven collection ------------------------------------------
def _declared_non_tests() -> list[str]:
    """Python paths the manifest declares as NOT collectable tests.

    Refuses loudly rather than silently collecting everything: an unreadable or
    empty manifest must not quietly widen the suite.
    """
    if not MANIFEST.is_file():
        raise RuntimeError(
            f"the test manifest is missing: {MANIFEST}. Collection membership is "
            "DECLARED, not discovered, so pytest will not guess."
        )
    excluded: list[str] = []
    declared = 0
    for line in MANIFEST.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        kind, entry = parts[0].strip(), parts[1].strip()
        if not entry.endswith(".py"):
            continue
        declared += 1
        if kind != "test":
            excluded.append(entry)
    if declared == 0:
        raise RuntimeError(
            f"{MANIFEST} declares 0 Python files. It covered only Wolfram files "
            "until AUDIT04-E; a manifest that declares nothing cannot govern "
            "collection, and silently collecting everything is the defect this "
            "replaced."
        )
    return excluded


collect_ignore = _declared_non_tests()
