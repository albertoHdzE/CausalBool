"""causalbool_paths -- the single owner of "where does this repository live".

AUDIT03, under the `monolithic-code` law: one concept, one owner, one file.

FOUR copies of `_repo_root` / `_paper_root` / `_paper_figures_dir` existed in
production Python -- Cancer_Corruption.py, Phase_Transition_Bio_Overlay.py,
KRB_Corruption_Anchors.py and Bayesian_Meta_Analysis.py. The AST census found
only three of them; the fourth was found by searching for a distinctive BODY
FRAGMENT ("CAUSALBOOL_PAPER_ROOT") rather than for the function name, which is
the search that finds copies after they have drifted.

And they HAD drifted, in the one helper that looked too small to matter:
`_paper_figures_dir` returned `str` in two files and `Path` in the other two.
A caller written against one signature and pointed at the other would have
concatenated a Path or divided a string.

  Owner returns `Path` -- the superset, since `str(Path)` is always available
  while the reverse is not. The two callers that need a string (both use the
  value as an `os.getenv` default) wrap it explicitly at the call site, so the
  conversion is visible where it is needed instead of baked into the helper.

`repo_root` adopts the DEPTH-INDEPENDENT form. The four production copies each
hard-coded `parents[2]`, which is correct only for a file exactly two levels
below the root and silently returns the wrong directory for anything else.
Walking up for the first ancestor holding both `src/` and `results/` gives the
identical answer at the four existing call sites (verified elementwise) and
keeps giving the right answer if a consumer moves.

DECLARED EXCEPTION -- workspaces/claude-nature/paper/code/{reproduce_all,
analysis_pipeline}.py keep their own copies. That tree is a FROZEN Level 8
reproducibility artefact (CLAUDE.md, "Historical execution artifacts"), and its
copies use `parents[4]` and a local search because they sit at a different
depth. Editing a frozen reproducibility workspace to remove a duplicate would
damage the artefact it exists to preserve. Recorded in GOVERNANCE/CORE.md.

Guarded by tools/check_single_engine.sh.
"""
from __future__ import annotations

import os
from pathlib import Path

__all__ = ["repo_root", "paper_root", "paper_figures_dir"]

PAPER_ROOT_ENV = "CAUSALBOOL_PAPER_ROOT"

# Ordered as the four collapsed copies ordered them; the first that exists wins.
_PAPER_CANDIDATES = (
    ("workspaces", "claude-nature", "paper"),
    ("workspaces", "level8-paper", "paper"),
    ("4ClaudeCode", "claude-Nature", "paper"),
)


def repo_root(start: Path | str | None = None) -> Path:
    """The repository root: the nearest ancestor holding both src/ and results/.

    ``start`` defaults to this module, so the answer does not depend on where
    the caller lives -- which is precisely the property the four hard-coded
    ``parents[2]`` copies lacked.
    """
    here = Path(start).resolve() if start is not None else Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / "src").is_dir() and (parent / "results").is_dir():
            return parent
    return Path(__file__).resolve().parents[1]


def paper_root() -> Path:
    """The Level 8 paper workspace. ``CAUSALBOOL_PAPER_ROOT`` overrides."""
    env = os.getenv(PAPER_ROOT_ENV)
    if env:
        return Path(env).expanduser().resolve()
    repo = repo_root()
    candidates = [repo.joinpath(*parts) for parts in _PAPER_CANDIDATES]
    for c in candidates:
        if c.is_dir():
            return c
    return candidates[-1]


def paper_figures_dir() -> Path:
    """Figures directory under :func:`paper_root`. Always a ``Path``."""
    return paper_root() / "figures"
