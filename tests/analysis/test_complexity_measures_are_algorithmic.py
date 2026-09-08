"""Every complexity measure in this programme is ALGORITHMIC. Two arms.

AUDIT04-E, author directive 2026-09-07. This programme is Kolmogorov/AID. The
two comparison measures are the INDEX-SET PROGRAM LENGTH (ours) and BDM. A
Shannon quantity may appear ONLY as an explicitly labelled statistical baseline
that our measure is compared against -- H_total and ZIP in comp_paper Table 2 --
never as a measure of ours.

WHY THIS FILE EXISTS ALONGSIDE test_description_length_is_algorithmic.py.

That file guards the four functions in src/description_lengths.py by matching
ENSEMBLE VOCABULARY: the words `entropy`, `shannon`, `Counter`, `probabilit`.
Measured on 2026-09-07, that regex catches entropy which is LABELLED and misses
entropy which is COMPUTED:

    "h = -sum(p * math.log2(p))  # entropy"   -> CAUGHT, via the comment
    "h = -sum(p * math.log2(p))"              -> MISSED
    D_v2's actual line                        -> MISSED

Its own positive control passes because of a code comment, so it never
exercised the thing it claims to detect. D_v2 sat behind it for the whole
programme computing Shannon binary entropy without once using the word.

ARM 1 is therefore SHAPE-based: p multiplied by its own logarithm, in any
spelling, anywhere under src/.

ARM 2 is the property that actually caught D_v2, and it is stronger than any
source scan because it does not care how the number is produced. A complexity
measure must not rank a RANDOM graph as simpler than a STRUCTURED one. Measured
over 200 random 12-node graphs each carrying exactly the 11 edges of a chain:

    D_v2 (Shannon, as it was)       195 / 200   97.5 %   <- inverted
    BDM                               0 / 200    0.0 %
    index-set program length         14 / 200    7.0 %

A source scan can be evaded by writing the entropy differently. This cannot: it
asks the measure to behave like a program length on inputs whose relative
complexity is not in doubt.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.description_lengths import row_run_index_set_length  # noqa: E402
from src.integration.Universal_D_v2_Encoder import UniversalDv2Encoder  # noqa: E402

# ---------------------------------------------------------------------------
# ARM 1 — computed entropy, not the word
# ---------------------------------------------------------------------------

# p * log(p) in any spelling, including the binary two-term form. Deliberately
# NOT keyed on identifier names: the point is the shape.
PLOGP = re.compile(
    r"(\w+)\s*\*\s*(?:math\.|np\.|numpy\.)?log2?\s*\([^()]*\b\1\b[^()]*\)"
    r"|(?:math\.|np\.|numpy\.)?log2?\s*\([^()]*\b(\w+)\b[^()]*\)\s*\*\s*\2\b"
)

# Files that legitimately hold a Shannon BASELINE, each with its reason. A
# baseline is a number our measure is compared against and beaten by; it is
# never returned as one of our complexity measures.
DECLARED_BASELINES = {
    "papers/method/code/complexity_analysis/complexity_analysis.py":
        "H_total is the statistical baseline in comp_paper Table 2, reported "
        "beside ZIP and beaten by BDM (580.01) and D_schema. Removing it would "
        "delete the comparison that demonstrates the algorithmic approach.",
    "src/complexity/Basin_Entropy.py":
        "_basin_entropy_shannon_baseline is the Krawitz-Shmulevich basin "
        "entropy, DEMOTED to a labelled baseline in AUDIT04-E. It is a property "
        "of the basin-size distribution, not a length, and nothing may quote it "
        "as a complexity. The primary return is basin_partition_bits, which is "
        "enumerative. Isolated in one function so the measure-returning code "
        "carries no distributional term.",
    "tests/analysis/test_description_length_is_algorithmic.py":
        "control strings for that file's own detector.",
    "tests/analysis/test_complexity_measures_are_algorithmic.py":
        "this file: the controls below are entropy on purpose.",
}


def _src_files() -> list[Path]:
    return [p for p in (ROOT / "src").rglob("*.py")
            if "__pycache__" not in p.parts and "external" not in p.parts]


def _docstring_lines(text: str) -> set[int]:
    """Line numbers occupied by docstrings.

    Prose must be able to quote the formula it is removing. Without this, every
    file that DOCUMENTS its retired entropy re-triggers the guard, and the fix
    for that would be to stop explaining -- which is the wrong direction. The
    predecessor stripped docstrings for the same reason.
    """
    import ast
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)) and node.body:
            if ast.get_docstring(node, clean=False) is not None:
                first = node.body[0]
                lines.update(range(first.lineno,
                                   (first.end_lineno or first.lineno) + 1))
    return lines


def test_no_computed_entropy_under_src():
    files = _src_files()
    assert files, "REFUSED: scanned 0 files under src/"
    offenders = []
    for p in files:
        rel = str(p.relative_to(ROOT))
        if rel in DECLARED_BASELINES:
            continue
        text = p.read_text(errors="replace")
        skip = _docstring_lines(text)
        for i, line in enumerate(text.splitlines(), 1):
            if i in skip:
                continue
            code = line.split("#", 1)[0]
            if PLOGP.search(code):
                offenders.append(f"{rel}:{i}: {line.strip()[:90]}")
    assert not offenders, (
        f"computed Shannon entropy under src/ ({len(offenders)} site(s), "
        f"{len(files)} files scanned):\n  " + "\n  ".join(offenders) +
        "\n\nA description length is a length in a declared language. If this is "
        "a deliberate BASELINE, declare it in DECLARED_BASELINES with its reason."
    )


@pytest.mark.parametrize("snippet,should_fire", [
    ("h -= p * math.log2(p)", True),
    ("h = -(p * math.log2(p) + (1 - p) * math.log2(1 - p))", True),   # D_v2's line
    ("type_entropy -= p * math.log2(p)", True),                       # MotifEncoder's
    ("entropy = -np.sum(q * np.log2(q))", True),
    ("bits = math.log2(n + 1)", False),                               # a code length
    ("cost += math.log2(math.comb(n, d))", False),                    # enumerative
    ("scale = x * math.log2(y)", False),                              # unrelated log
])
def test_arm1_control(snippet, should_fire):
    """CONTROL. The predecessor's control passed on a COMMENT; this one may not.

    Note the second case carries no word an English reader would recognise as
    entropy, and the two negative cases are legitimate code lengths that must
    not fire.
    """
    assert bool(PLOGP.search(snippet)) is should_fire, snippet


# ---------------------------------------------------------------------------
# ARM 2 — the ordering property, which no source scan can give
# ---------------------------------------------------------------------------

def _chain(n: int) -> np.ndarray:
    m = np.zeros((n, n), dtype=int)
    for i in range(n - 1):
        m[i, i + 1] = 1
    return m


def _random_with_same_edges(n: int, edges: int, rng) -> np.ndarray:
    m = np.zeros((n, n), dtype=int)
    for k in rng.choice(n * n, edges, replace=False):
        m[k // n, k % n] = 1
    return m


def _bdm_2d(m):
    from pybdm import BDM
    return float(BDM(ndim=2).bdm(np.asarray(m, dtype=np.uint8)))


def _index_set(m):
    return float(row_run_index_set_length(m))


def _dv2(m):
    return float(UniversalDv2Encoder(m).compute()["dv2"])


MEASURES = {"index_set": _index_set, "bdm": _bdm_2d, "dv2_forwarder": _dv2}


@pytest.mark.parametrize("name", sorted(MEASURES))
def test_random_is_not_simpler_than_a_chain(name):
    """The property that exposed D_v2 at 195/200.

    A threshold rather than 0 because the index-set length legitimately ties on
    some draws -- a random graph can happen to have a compressible row pattern.
    It sat at 7.0 per cent when this was written; 25 per cent is far below the
    97.5 per cent of an inverted measure and far above honest jitter.
    """
    n, trials = 12, 60
    rng = np.random.default_rng(11)
    chain = _chain(n)
    fn = MEASURES[name]
    ref = fn(chain)
    inverted = sum(1 for _ in range(trials)
                   if fn(_random_with_same_edges(n, int(chain.sum()), rng)) <= ref)
    assert inverted / trials < 0.25, (
        f"{name} ranked a RANDOM graph simpler-or-equal than a chain in "
        f"{inverted}/{trials} draws. A measure that orders random below "
        f"structured is inverted, not mis-tuned."
    )


def test_arm2_can_fail():
    """CONTROL for arm 2: the retired Shannon encoder must FAIL this property.

    Reconstructed here rather than imported, since the original was replaced by
    a forwarder in the same commit. If this ever stops failing, the property is
    no longer discriminating and arm 2 has become decoration.
    """
    def retired_dv2(m, block_sizes=(4, 5, 6)) -> float:
        m = np.asarray(m, dtype=int)
        n = m.shape[0]
        total = 0.0
        for b in block_sizes:
            pad = (b - (n % b)) % b
            mm = np.pad(m, ((0, pad), (0, pad))) if pad else m
            nn = mm.shape[0]
            counts: dict[tuple[int, int], int] = {}
            for i in range(0, nn - b + 1):
                for j in range(0, nn - b + 1):
                    blk = mm[i:i + b, j:j + b]
                    counts[(blk.size, int(blk.sum()))] = \
                        counts.get((blk.size, int(blk.sum())), 0) + 1
            for (size, ones), c in counts.items():
                p = 1.0 if ones else 0.0          # the canonical block it rebuilt
                h = 0.0 if p in (0.0, 1.0) else \
                    -(p * math.log2(p) + (1 - p) * math.log2(1 - p))
                total += h * size + math.log2(c)
        return total

    n, trials = 12, 60
    rng = np.random.default_rng(11)
    chain = _chain(n)
    ref = retired_dv2(chain)
    inverted = sum(1 for _ in range(trials)
                   if retired_dv2(_random_with_same_edges(n, int(chain.sum()), rng)) <= ref)
    assert inverted / trials >= 0.25, (
        "the retired Shannon encoder no longer fails the ordering property, so "
        "the property has stopped discriminating and arm 2 is decoration"
    )
