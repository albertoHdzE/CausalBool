"""Unit tests for src/causalbool_paths.py — the owner that had none.

AUDIT03-C. This module was created in the previous pass to collapse four
duplicated copies of `_repo_root` / `_paper_root` / `_paper_figures_dir`, and it
shipped with a parity probe (24/24 against the copies it replaced) but with NO
UNIT TESTS. Coverage measured it at zero. A collapse verified only against the
copies it replaced is verified against the past, not against a contract.

The two properties worth pinning are the two the old copies got wrong:

  * `_paper_figures_dir` returned `str` in two files and `Path` in two others,
    so a caller written against one signature and handed the other would have
    concatenated a Path or divided a string;
  * every copy hard-coded `parents[2]`, which is correct only for a file exactly
    two levels below the root and silently returns the wrong directory otherwise.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import causalbool_paths as cp  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_env():
    """The override must not leak between tests."""
    saved = os.environ.pop(cp.PAPER_ROOT_ENV, None)
    yield
    os.environ.pop(cp.PAPER_ROOT_ENV, None)
    if saved is not None:
        os.environ[cp.PAPER_ROOT_ENV] = saved


# ── repo_root ───────────────────────────────────────────────────────────────

def test_repo_root_finds_this_repository():
    r = cp.repo_root()
    assert (r / "src").is_dir() and (r / "results").is_dir()
    assert r == ROOT


@pytest.mark.parametrize("start", [
    "src/analysis/Cancer_Corruption.py",      # two levels down
    "src/stats/Bayesian_Meta_Analysis.py",    # two levels down
    "tools/check_core_index.sh",              # ONE level down
    "src/Packages/Integration/Gates.m",       # three levels down
])
def test_repo_root_is_depth_independent(start):
    """The property the four collapsed copies lacked.

    Each hard-coded `parents[2]`, so it was right only at depth two. This must
    give the same answer from any depth, which is what makes it safe for a
    consumer to move.
    """
    assert cp.repo_root(ROOT / start) == ROOT


def test_repo_root_hardcoded_parents_two_would_have_been_wrong():
    """The negative control: show the old rule actually disagrees.

    Without this, "depth-independent" is an untested adjective.
    """
    one_level_down = ROOT / "tools" / "check_core_index.sh"
    old_rule = one_level_down.resolve().parents[2]
    assert old_rule != ROOT
    assert cp.repo_root(one_level_down) == ROOT


# ── BOTH markers, not either: the AUDIT04 mutation gap ──────────────────────
#
# AUDIT04 Phase A. The mutant `py-paths-root` loosens the ancestor test from
# "holds src/ AND results/" to OR, and it was PRE-REGISTERED to survive: the
# tests above pass start paths only under src/ and tools/, neither of which
# holds either marker, so none of them can tell the two rules apart.
#
# It was killed -- but by `closure:wolfram` alone, with ZERO pytest kills. A
# mutant caught only by a governance gate is not a tested mutant, so the gap is
# real and these are the tests that close it.
#
# The expected values below come from the CONTRACT in the docstring ("the
# nearest ancestor holding both src/ and results/"), not from running the code.

def test_an_ancestor_with_only_results_is_not_the_root(tmp_path):
    """`results/` alone must NOT satisfy the rule.

    This is the exact shape that exists in this repository: `tests/` holds
    `results/` and no `src/`. Under OR it would be returned as the root and
    every consumer would build paths one level too deep.
    """
    proj = tmp_path / "proj"
    (proj / "results").mkdir(parents=True)
    (proj / "deep" / "deeper").mkdir(parents=True)
    assert cp.repo_root(proj / "deep" / "deeper" / "x.py") != proj


def test_an_ancestor_with_only_src_is_not_the_root(tmp_path):
    """The mirror case: `src/` alone must not satisfy it either."""
    proj = tmp_path / "proj"
    (proj / "src").mkdir(parents=True)
    (proj / "deep").mkdir(parents=True)
    assert cp.repo_root(proj / "deep" / "x.py") != proj


def test_an_ancestor_with_both_markers_is_the_root(tmp_path):
    """The positive half. Without it the two tests above would pass for a
    function that never returns anything."""
    proj = tmp_path / "proj"
    (proj / "src").mkdir(parents=True)
    (proj / "results").mkdir(parents=True)
    (proj / "a" / "b").mkdir(parents=True)
    assert cp.repo_root(proj / "a" / "b" / "x.py") == proj


def test_nearest_ancestor_wins_over_a_higher_one(tmp_path):
    """"Nearest" is load-bearing: an outer directory also carrying both markers
    must not win over an inner one."""
    outer = tmp_path / "outer"
    (outer / "src").mkdir(parents=True)
    (outer / "results").mkdir(parents=True)
    inner = outer / "sub" / "inner"
    (inner / "src").mkdir(parents=True)
    (inner / "results").mkdir(parents=True)
    assert cp.repo_root(inner / "deep.py") == inner


def test_a_start_under_tests_returns_the_repository_not_tests():
    """The real-repository instance of the same defect, named in advance.

    `tests/` carries `results/` but no `src/`, so OR returns `tests/` here.
    """
    assert not (ROOT / "tests" / "src").is_dir()
    assert (ROOT / "tests" / "results").is_dir(), \
        "precondition: this test is only meaningful while tests/results exists"
    assert cp.repo_root(Path(__file__)) == ROOT


def test_a_self_contained_subproject_is_its_own_root():
    """Not a defect -- a consequence of the contract, pinned so it stays visible.

    `index-deconvolution/` carries both markers, so it IS the nearest ancestor
    holding both and is returned as the root for files inside it. Any consumer
    living there resolves to the subproject, not to the repository.
    """
    sub = ROOT / "index-deconvolution"
    if not ((sub / "src").is_dir() and (sub / "results").is_dir()):
        pytest.skip("LOUD SKIP: index-deconvolution no longer carries both markers")
    assert cp.repo_root(sub / "src" / "deconvolution.py") == sub


def test_falls_back_when_no_ancestor_carries_both(tmp_path):
    """The final `return` -- reached only when the walk finds nothing.

    It must return this repository rather than raising or returning the walk's
    last element, because callers build paths from the result unconditionally.
    """
    lonely = tmp_path / "nothing" / "here"
    lonely.mkdir(parents=True)
    assert cp.repo_root(lonely / "x.py") == ROOT


# ── paper_root ──────────────────────────────────────────────────────────────

def test_paper_root_is_under_the_repo_by_default():
    p = cp.paper_root()
    assert isinstance(p, Path)
    assert str(p).startswith(str(cp.repo_root()))


def test_env_override_wins_and_is_resolved(tmp_path):
    target = tmp_path / "somewhere" / "paper"
    target.mkdir(parents=True)
    os.environ[cp.PAPER_ROOT_ENV] = str(target)
    assert cp.paper_root() == target.resolve()


def test_env_override_expands_a_user_path():
    os.environ[cp.PAPER_ROOT_ENV] = "~/definitely-not-a-real-paper-root"
    got = cp.paper_root()
    assert "~" not in str(got)
    assert got.is_absolute()


def test_paper_root_falls_back_to_the_last_candidate_when_none_exist(monkeypatch):
    """With no candidate on disk it must return the LAST one, deterministically,
    rather than raising or returning the repo root -- callers build paths from
    it and a silent repo-root return would scatter figures into the tree."""
    monkeypatch.setattr(cp, "repo_root", lambda *a, **k: Path("/nonexistent-xyz"))
    got = cp.paper_root()
    assert got == Path("/nonexistent-xyz").joinpath(*cp._PAPER_CANDIDATES[-1])


def test_candidate_order_is_declared_and_stable():
    assert cp._PAPER_CANDIDATES[0] == ("workspaces", "claude-nature", "paper")
    assert len(cp._PAPER_CANDIDATES) == 3


# ── paper_figures_dir: the drift that this module exists to end ─────────────

def test_figures_dir_returns_a_path_not_a_string():
    """THE regression this owner was created to prevent.

    Before the collapse this returned `str` in Cancer_Corruption.py and
    Bayesian_Meta_Analysis.py, and `Path` in Phase_Transition_Bio_Overlay.py and
    KRB_Corruption_Anchors.py. Path is the superset -- str(Path) is always
    available, the reverse is not -- and the two callers that need a string now
    wrap it at the call site where the conversion is visible.
    """
    got = cp.paper_figures_dir()
    assert isinstance(got, Path)
    assert not isinstance(got, str)


def test_figures_dir_is_exactly_figures_under_paper_root():
    assert cp.paper_figures_dir() == cp.paper_root() / "figures"


def test_figures_dir_follows_the_env_override(tmp_path):
    os.environ[cp.PAPER_ROOT_ENV] = str(tmp_path)
    assert cp.paper_figures_dir() == tmp_path.resolve() / "figures"


def test_the_public_surface_is_declared():
    assert set(cp.__all__) == {"repo_root", "paper_root", "paper_figures_dir"}
