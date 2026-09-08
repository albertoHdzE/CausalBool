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


# --- the structured families, and where each measure fails on them ----------
#
# AUDIT04-F. The chain test above uses one structured object. That is one
# family, and a measure can pass it while inverting on another -- which is
# exactly what happens. Measured 2026-09-07 at n = 16 against 20 random matrices
# of IDENTICAL edge count (structured bits / random-mean bits):
#
#   family              index-set          BDM
#   checkerboard        1050.5 / 563.9     34.3 / 489.9
#   column stripes      1050.5 / 568.4     34.2 / 485.2
#   two diagonal blocks  134.9 / 555.1     50.0 / 485.3
#   band, in-degree 4    134.9 / 439.8     85.3 / 444.7
#   band, in-degree 8    134.9 / 566.7    108.3 / 488.4
#
# The index-set length INVERTS on the first two. That is not a tuning error: it
# is a run-length code over each row's neighbour index set, and an alternating
# row costs n/2 runs, its maximum, while its algorithmic content is nearly nil.
#
# THIS TEST IS WRITTEN TO THE MEASUREMENT, NOT TO A PASS. The two known
# inversions are declared below with their reason, and the test fails if a
# declared inversion silently disappears as well as if a new one appears. A
# guard that hides a known failure is worse than no guard, because it converts
# a documented limitation into an invisible one.

def _checkerboard(n):
    return np.fromfunction(lambda i, j: ((i + j) % 2 == 0).astype(int), (n, n), dtype=int)


def _column_stripes(n):
    return np.tile(np.array([1, 0] * (n // 2)), (n, 1))


def _two_blocks(n):
    h = n // 2
    return np.block([[np.ones((h, h), int), np.zeros((h, h), int)],
                     [np.zeros((h, h), int), np.ones((h, h), int)]])


def _band(n, k):
    m = np.zeros((n, n), dtype=int)
    for i in range(n):
        for j in range(k):
            m[i, (i + j) % n] = 1
    return m


FAMILIES = {
    "checkerboard": lambda n: _checkerboard(n),
    "column_stripes": lambda n: _column_stripes(n),
    "two_blocks": lambda n: _two_blocks(n),
    "band_k4": lambda n: _band(n, 4),
    "band_k8": lambda n: _band(n, 8),
}

# Declared, reasoned exceptions: (measure, family) pairs known to invert.
DECLARED_INVERSIONS = {
    ("index_set", "checkerboard"):
        "run-length code over rows; an alternating row costs n/2 runs, its "
        "maximum. Measured 1050.5 bits against 563.9 for random of equal density.",
    ("index_set", "column_stripes"):
        "same cause as checkerboard: every row alternates, so every row is "
        "priced at the code's worst case. Measured 1050.5 against 568.4.",
}


@pytest.mark.parametrize("family", sorted(FAMILIES))
@pytest.mark.parametrize("measure", ["index_set", "bdm"])
def test_structured_families_against_matched_random(measure, family):
    n, trials = 16, 20
    rng = np.random.default_rng(1)
    a = FAMILIES[family](n)
    edges = int(a.sum())
    fn = MEASURES[measure]
    ref = fn(a)
    randoms = [fn(_random_with_same_edges(n, edges, rng)) for _ in range(trials)]
    mean_random = float(np.mean(randoms))
    inverted = ref >= mean_random
    declared = (measure, family) in DECLARED_INVERSIONS

    if declared:
        assert inverted, (
            f"{measure} on {family} was DECLARED to invert, and it no longer "
            f"does ({ref:.1f} bits vs {mean_random:.1f} for matched random). "
            f"That is good news, but the declaration in DECLARED_INVERSIONS and "
            f"in Universal_D_v2_Encoder is now stale and must be removed in the "
            f"same commit as the fix.\nReason on record: "
            f"{DECLARED_INVERSIONS[(measure, family)]}")
    else:
        assert not inverted, (
            f"{measure} ranked the structured family '{family}' at {ref:.1f} "
            f"bits against {mean_random:.1f} for random matrices of IDENTICAL "
            f"edge count ({edges} edges, n={n}) -- it calls the structured "
            f"object at least as complex as noise. This is a NEW inversion: it "
            f"is not in DECLARED_INVERSIONS.")


def test_schema_length_is_blind_to_rewiring_so_cannot_serve_the_null_test():
    """Sigma_v D_schema is EXACTLY invariant under degree-preserving rewiring.

    AUDIT04-F, and this is the fact that decides the forwarder's target. Our
    per-node measure, schema_normal_form_length (Variant E in
    src/description_lengths.py), prices a node from (n, gate, in-degree) alone:
    a self-delimiting clause count, then per clause log2(n+1) + log2(C(n,k)) + k.
    None of those terms reads WHICH coordinates are involved. The null this
    experiment uses -- Null_Generator_HPC.degree_preserving_swap -- preserves
    in-degree by construction.

    So the real network and every one of its degree-preserving nulls get the
    same number, and the difference is not small, it is zero. Our mechanism-side
    measure cannot answer a wiring question. That is not a weakness in the
    measure; a wiring question is simply not what it measures, which is why the
    encoder reports BDM alongside it rather than repointing at D_schema.

    Written as a test so that nobody repoints it in six months.
    """
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2] / "src"))
    from experiments.Null_Generator_HPC import degree_preserving_swap

    from src.description_lengths import schema_normal_form_length

    def sigma_d_schema(adj, gates):
        """Sigma_v D_schema for a network, from its wiring and its gates.

        Each node's LOCAL truth table is built from its gate and its actual
        in-degree, which is the only thing the measure can see.
        """
        n = adj.shape[0]
        total = 0.0
        for v in range(n):
            d = int(adj[:, v].sum())
            if d == 0:
                continue
            if gates[v] == "OR":
                tt = [1 if x else 0 for x in range(2 ** d)]
            else:
                tt = [bin(x).count("1") % 2 for x in range(2 ** d)]
            total += schema_normal_form_length(tt, n)
        return total

    n = 10
    rng = np.random.default_rng(3)
    adj = np.zeros((n, n), dtype=int)
    for j in range(n):
        for i in rng.choice([k for k in range(n) if k != j], 3, replace=False):
            adj[i, j] = 1
    gates = ["OR" if v % 2 else "XOR" for v in range(n)]

    rewired = degree_preserving_swap(adj, nswap_factor=10, seed=7)
    assert not np.array_equal(adj, rewired), (
        "the null did not actually rewire anything, so the invariance below "
        "would be vacuous")
    assert (adj.sum(axis=0) == rewired.sum(axis=0)).all(), (
        "degree_preserving_swap did not preserve in-degrees; the claim under "
        "test depends on it doing so")

    before = sigma_d_schema(adj, gates)
    after = sigma_d_schema(rewired, gates)
    assert after == before, (
        f"Sigma_v D_schema moved under a degree-preserving rewiring "
        f"({before:.4f} -> {after:.4f} bits). It should be EXACTLY invariant: "
        f"the measure reads (n, gate, in-degree) and the null preserves all "
        f"three. If this ever fails, the measure has gained a wiring-sensitive "
        f"term and the reasoning that kept it out of the null experiment must "
        f"be revisited.")
    assert before > 0.0

    n = 8
    or3 = [1 if x else 0 for x in range(2 ** 3)]
    xor3 = [bin(x).count("1") % 2 for x in range(2 ** 3)]

    # And the discriminating half: it DOES separate different mechanisms, so the
    # invariance above is specific to rewiring, not general blindness.
    assert schema_normal_form_length(xor3, n) > schema_normal_form_length(or3, n), (
        "D_schema must still separate XOR from OR at equal in-degree -- that "
        "separation is the whole point of GLOSSARY sec.1d. If this fails the "
        "measure has collapsed to the narrow reading of the sumandos.")


def test_the_encoder_reports_both_measures_and_never_merges_them():
    """AUDIT04-F. Two named measures side by side, per the author's directive.

    Decision #96 forbids folding two measures into one number with a selector
    bit, so the assertion is not merely that both keys exist -- it is that the
    retained `dv2` key still carries the INDEX-SET value unchanged, so the
    thirteen existing callers and every stored artefact keep resolving.
    """
    chain = _chain(12)
    res = UniversalDv2Encoder(chain).compute()

    assert res["dv2"] == res["index_set_bits"], (
        "`dv2` must keep carrying the index-set length; thirteen callers and "
        "the stored artefacts read that key")
    assert res["dv2"] == pytest.approx(row_run_index_set_length(chain))
    assert res["bdm"] == pytest.approx(_bdm_2d(chain))
    assert set(res["measures"]) == {"index_set_program_length", "bdm"}
    # The two must be genuinely different numbers, or "reporting both" is theatre.
    assert res["bdm"] != pytest.approx(res["index_set_bits"])


def test_bdm_below_its_partition_floor_is_none_and_says_why_not_zero():
    """A network too small to measure must not read as `0 bits`.

    pybdm's 2-D partition is 4x4 and refuses smaller input. AUDIT02/P1: a silent
    zero is indistinguishable from a real measurement of zero, and here it would
    make the smallest networks look like the simplest possible ones.
    """
    tiny = np.array([[0, 1], [1, 0]])
    res = UniversalDv2Encoder(tiny).compute()
    assert res["bdm"] is None
    assert res["dv2"] > 0.0, "the index-set length has no such floor"
    note = res["detail"]["bdm_note"]
    assert note and "not zero" in note.lower() and "4x4" in note.lower()


def test_compute_both_agrees_with_the_encoder_it_delegates_to():
    """The null generator's pair helper must not be a second implementation."""
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2] / "src"))
    from experiments.Null_Generator_HPC import compute_both

    a = _chain(12)
    both = compute_both(a)
    res = UniversalDv2Encoder(a).compute()
    assert both["index_set"] == pytest.approx(res["index_set_bits"])
    assert both["bdm"] == pytest.approx(res["bdm"])


def test_the_scaling_exponent_refuses_rather_than_returning_zero():
    """AUDIT02/P1: a silent 0.0 is indistinguishable from a real measurement.

    The block-size sweep D(b) ~ b^alpha is meaningful only for a
    block-decomposed measure. With D_v2 forwarding to a program length there is
    no block size, so every point returned the same value and the fitted slope
    was exactly 0.0 for every network -- measured Alpha(Rand) 0.0000 and
    Alpha(Struct) 0.0000. Zero is a legitimate scaling exponent, so returning it
    would put a fabricated measurement into a tracked artefact.

    Both refusal paths are pinned: the standalone marker and the live call site.
    """
    from src.complexity.Scaling_LZ_Tools import ComplexityScaler
    from src.integration.Universal_D_v2_Encoder import scaling_exponent_unavailable

    with pytest.raises(NotImplementedError, match="block"):
        scaling_exponent_unavailable(np.zeros((6, 6), dtype=int))

    with pytest.raises(NotImplementedError, match="block size"):
        ComplexityScaler.compute_scaling_exponent(np.zeros((8, 8), dtype=int))


def test_the_forwarder_works_without_a_conftest():
    """The bridge condition, in a SUBPROCESS, because pytest cannot reproduce it.

    The forwarder does `from src.description_lengths import ...`, which needs the
    repo root on sys.path. Under pytest the root conftest.py always puts it
    there, so the guarding branch never executes and the dependency is invisible.
    Everywhere else it is not there.

    It failed in exactly one place: TSK-NATURE-LEV3-SETUP-002 is a Wolfram test
    that shells out to Python through BioBridgeV2, where no conftest runs. The
    whole MUnit suite went red with `ModuleNotFoundError: No module named 'src'`
    while the pure tier stayed 11/11 green, and only the pre-push Wolfram tier
    caught it.

    A subprocess with `src` on the path but NOT the root is that condition
    exactly, so this pins the fix rather than the environment that hides it.
    """
    import subprocess
    import textwrap

    code = textwrap.dedent(f"""
        import sys
        sys.path.insert(0, {str(ROOT / 'src')!r})
        assert {str(ROOT)!r} not in sys.path, "the root must NOT be importable here"
        import numpy as np
        from integration.Universal_D_v2_Encoder import UniversalDv2Encoder
        m = np.zeros((6, 6), dtype=int)
        m[0, 1] = m[1, 2] = m[2, 3] = 1
        r = UniversalDv2Encoder(m).compute()
        assert r["measure"] == "index_set_program_length", r
        assert r["dv2"] > 0, r
        print("OK", r["dv2"])
    """)
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True,
                          text=True, cwd="/tmp")
    assert proc.returncode == 0, (
        f"the forwarder does not work without a conftest:\n{proc.stderr[-1500:]}")
    assert proc.stdout.startswith("OK"), proc.stdout


def test_the_separation_operator_beats_the_z_score_it_replaced():
    """ARM 3 — the COMPARISON operator, not the measure (AUDIT04-E).

    A z-score rescales a quantity in BITS by the standard deviation of an
    ensemble, which is a distributional summary wrapped around an algorithmic
    length. Three nulls where bio beats 0 of 1000 in every case -- identical
    evidence -- and the z-score falsifies two of them:

        gaussian        z 5.07  pass       gap  8.8 bits   rank 0/1000
        DEGENERATE      z 0.00  FALSIFY    gap 50.0 bits   rank 0/1000
        heavy-tailed    z 0.31  FALSIFY    gap 20.0 bits   rank 0/1000

    The degenerate case is the old code's own `if sd > 0 else 0.0` branch:
    every null 50 bits LONGER than bio, reported as no evidence. This pins that
    the replacement does not repeat it.
    """
    def zscore(x, xs):                       # the retired operator, verbatim
        mu = float(np.mean(xs))
        sd = float(np.std(xs)) if len(xs) > 1 else 0.0
        return (mu - x) / sd if sd > 0 else 0.0

    def gap_and_rank(x, xs):
        return min(xs) - x, sum(1 for v in xs if v <= x) / len(xs)

    rng = np.random.default_rng(0)
    cases = {
        "gaussian": list(rng.normal(160, 8, 1000)),
        "degenerate": [170.0] * 1000,
        "heavy_tailed": list(140 + rng.pareto(1.2, 1000) * 12),
    }
    bio = 120.0
    z_falsified, sep_falsified = 0, 0
    for xs in cases.values():
        gap, exceed = gap_and_rank(bio, xs)
        assert exceed == 0.0, "fixture broken: bio must beat every null"
        assert gap > 0.0
        z_falsified += int(zscore(bio, xs) < 2.0)          # old rule
        sep_falsified += int(exceed >= 0.05 or gap <= 0.0)  # new rule

    assert sep_falsified == 0, (
        "the replacement falsified a case where bio beat every null")
    assert z_falsified == 2, (
        "the z-score no longer fails these cases, so this control has stopped "
        f"discriminating (got {z_falsified}, expected 2)")


def test_the_monitor_refuses_a_missing_separation():
    """The old default was z = -999.0, which silently satisfied `z < 2.0`.

    A redirection decided from an absent measurement is worse than a crash, because
    it looks like a decision.
    """
    from src.pipeline.Contingency_Monitor import ContingencyMonitor

    with pytest.raises(ValueError, match="gap_bits_deg"):
        ContingencyMonitor.evaluate_checkpoint({"aer": 1.5, "rho_depmap": 0.6})


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
