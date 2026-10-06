"""Focused tests for gap-ranking-v1-r1 (PROTOCOL.md §6).  Fixtures: ../fixtures.json.

Run with the declared route on PYTHONPATH (see ../run.sh).  GGAP_SRC may point to a
mutated copy of ../src for the mutation harness.
"""
from __future__ import annotations

import inspect
import itertools
import json
import os
import subprocess
import sys
from fractions import Fraction

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.dirname(HERE)
SRC = os.environ.get("GGAP_SRC", os.path.join(RUN, "src"))
sys.path.insert(0, os.path.join(RUN, "src"))
if SRC != os.path.join(RUN, "src"):
    sys.path.insert(0, SRC)                 # mutated gapscore.py shadows the original only

import gapscore as G  # noqa: E402
import join as J  # noqa: E402
import routes  # noqa: E402
from seqdecon.operators import gaps, token_occurrence_frames  # noqa: E402

with open(os.path.join(RUN, "fixtures.json")) as _fh:
    FX = json.load(_fh)


def recs_for(states_list, block):
    return G.occurrence_records(states_list, [tuple(block)])


def by_value(recs, traj=0):
    return {r["value"]: r for r in recs if r["traj"] == traj}


def wo(rows):
    return {(w, o): {"regular": r, "eligible": e, "available": e > 0} for w, o, r, e in rows}


# --- occurrence extraction (through the producer path) ----------------------------

def test_tok_fixture_frames_and_gaps():
    f = FX["F_TOK"]
    recs = by_value(recs_for([f["tokens"]], [0, 2]))   # 2-bit block: token == state
    assert recs[f["value"]]["frames"] == f["frames"]
    assert recs[f["value"]]["gaps"] == f["gaps"]
    assert gaps(token_occurrence_frames(f["tokens"], f["value"])) == f["gaps"]


def test_constant_tokens_keep_every_frame():
    f = FX["F_CONST"]
    recs = by_value(recs_for([f["tokens"]], [0, 3]))
    assert recs[f["value"]]["frames"] == f["frames"]
    assert recs[f["value"]]["eligible"] and recs[f["value"]]["regular"]


@pytest.mark.parametrize("key", ["F_ABSENT", "F_EMPTY"])
def test_absent_and_empty(key):
    f = FX[key]
    assert token_occurrence_frames(f["tokens"], f["value"]) == f["frames"]


@pytest.mark.parametrize("tokens, value", [tuple(x) for x in FX["F_MALFORMED"]])
def test_malformed_refused(tokens, value):
    with pytest.raises(ValueError):
        token_occurrence_frames(tokens, value)


def test_malformed_state_gives_no_partial_output():
    with pytest.raises(ValueError):
        G.occurrence_records([[1, 0, 1, -1]], [(0, 1)])


def test_eligibility_and_regularity():
    f = FX["F_ELIG"]
    reg = by_value(recs_for([f["regular_states"]], [0, 1]))
    irr = by_value(recs_for([f["irregular_states"]], [0, 1]))
    for got, want in ((reg[1], f["regular"]), (irr[1], f["irregular"]), (reg[0], f["two"])):
        assert got["frames"] == want["frames"]
        assert got["eligible"] == want["eligible"] and got["regular"] == want["regular"]


def test_trajectories_never_joined():
    f = FX["F_JOIN"]
    recs = recs_for(f["trajectories"], f["block"])
    assert G.pooled_score(recs) == f["pooled"]
    assert all(not r["eligible"] for r in recs)


def test_counting_pool_differs_from_mean_of_fractions():
    f = FX["F_POOL"]
    recs = recs_for(f["trajectories"], f["block"])
    assert G.pooled_score(recs) == f["pooled"]
    per = []
    for t in range(2):
        e = sum(1 for r in recs if r["traj"] == t and r["eligible"])
        g = sum(1 for r in recs if r["traj"] == t and r["regular"])
        per.append(Fraction(g, e))
    assert sum(per) / 2 == Fraction(*f["mean_of_fractions"])
    assert G.as_fraction(G.pooled_score(recs)) != sum(per) / 2


def test_frame_counts_and_sampling():
    f = FX["F_FRAMES"]
    xs = list(range(f["steps"] + 1))
    for tau, k in f["frames"].items():
        assert len(G.sample(xs, int(tau))) == k
    assert G.sample(xs, 16) == f["sample_tau16_of_range65"]


def test_nonzero_origins_and_ragged_blocks():
    import study as S
    f = FX["F_BLOCKS"]
    for key, (w, o) in (("w3o1", (3, 1)), ("w4o3", (4, 3)), ("w3o2", (3, 2))):
        blocks = S.partition(w, o, f["n"])
        assert [list(b) for b in blocks] == f[key]["blocks"]
        assert [G.block_tokens([f["x"]], a, ln)[0] for a, ln in blocks] == f[key]["tokens"]


def test_start_states():
    assert G.start_states(8) == [0, 1, 128, 255, 0b01010101, 0b10101010]
    assert G.start_states(10) == [0, 1, 512, 1023, 0b0101010101, 0b1010101010]


# --- ranking ------------------------------------------------------------------------

def test_rank_ties_zero_unavailable_inheritance_duplicates():
    f = FX["F_RANK"]
    order = G.rank(f["candidates"], wo(f["wo_scores"]))
    assert order == f["order"]
    assert len(order) == len(f["candidates"])           # duplicates survive


def test_rank_exact_rational_comparison():
    f = FX["F_TOL"]
    assert G.rank(f["candidates"], wo(f["wo_scores"])) == f["order"]


def test_rank_takes_no_labels():
    assert list(inspect.signature(G.rank).parameters) == ["cands", "wo_scores"]


def test_population_excludes_exactly_the_eleven_controls():
    import study as S
    for n, N in ((8, 124), (10, 130)):
        cands = S.candidates(n)
        kept = [c for c in cands if G.is_ranked(c)]
        assert len(kept) == N
        dropped = [c for c in cands if not G.is_ranked(c)]
        assert sorted((c["family"], c["g"]) for c in dropped) == sorted(
            [("F1", "val")] * 9 + [("C", "identity"), ("C", "constant")])


# --- endpoint -----------------------------------------------------------------------

def test_expected_first_rank_by_enumeration():
    f = FX["F_EXP"]
    perms = list(itertools.permutations(range(f["N"])))
    assert len(perms) == f["permutations"]
    full = set(range(f["m"]))
    total = sum(1 + next(i for i, c in enumerate(p) if c in full) for p in perms)
    assert Fraction(total, len(perms)) == f["expected_first_rank"] == Fraction(
        f["N"] + 1, f["m"] + 1)


def _cell(gap_order, ids=None):
    ids = ids if ids is not None else sorted(gap_order)
    return {"model": "M1", "tau": 1, "gap_order": gap_order, "canonical_order": sorted(ids),
            "candidates": [{"id": i, "candidate": {"family": "F2", "g": "par"}, "score": None}
                           for i in ids]}


def _labels(full, ids):
    return {("M1", i, 1): {"candidate": {"family": "F2", "g": "par"},
                           "status": "FULL" if i in full else "AUT-FAIL"} for i in ids}


def test_endpoint_fixture():
    f = FX["F_ENDPOINT"]
    c = J.cell_endpoint(_cell(f["gap_order"]), _labels(set(f["full"]), range(5)), {})
    assert (c["r_G"], c["r_C"]) == (f["r_G"], f["r_C"])
    assert [c["random_expected"]["num"], c["random_expected"]["den"]] == f["random_expected"]
    assert c["delta_random"] == f["delta_random"] and c["delta_canonical"] == f["delta_canonical"]
    assert (c["vs_random"], c["vs_canonical"]) == ("LATER", "TIE")
    assert c["first_hit"]["dynamics"] == "NOT_CHARACTERISED"


def test_no_full_reference_is_unavailable_not_zero():
    c = J.cell_endpoint(_cell([0, 1, 2]), _labels(set(), range(3)), {})
    assert c["status"] == "NO_FULL_REFERENCE"
    assert c["r_G"] is None and c["random_expected"] is None and c["vs_random"] is None


def test_missing_outcome_fails():
    with pytest.raises(J.JoinError):
        J.cell_endpoint(_cell([0, 1, 2]), _labels({1}, range(2)), {})


def test_missing_rank_entry_fails():
    with pytest.raises(J.JoinError):
        J.cell_endpoint(_cell([0, 1], ids=[0, 1, 2]), _labels({1}, range(3)), {})


def test_shuffled_labels_do_not_change_ranks():
    order = [3, 1, 2, 0, 4]
    a = J.cell_endpoint(_cell(list(order)), _labels({2, 4}, range(5)), {})
    b = J.cell_endpoint(_cell(list(order)), _labels({0, 1}, range(5)), {})
    assert a["gap_order"] == b["gap_order"] == order
    assert a["r_G"] != b["r_G"]


def _results_d_copy(tmp_path, mutate):
    lines = open(J.RESULTS_D).read().splitlines()
    lines = mutate(lines)
    p = tmp_path / "results_d.jsonl"
    p.write_text("\n".join(lines) + "\n")
    return str(p)


def test_trusted_hash_refuses_a_modified_copy(tmp_path):
    p = _results_d_copy(tmp_path, lambda ls: ls[:-1])
    with pytest.raises(J.JoinError, match="hash"):
        J.load_labels(p)


def test_missing_and_duplicate_outcome_ids_fail(tmp_path):
    p = _results_d_copy(tmp_path, lambda ls: ls[:-1])
    with pytest.raises(J.JoinError, match="coverage"):
        J.load_labels(p, expect_sha=routes.sha256(p))
    q = _results_d_copy(tmp_path, lambda ls: ls + ls[-1:])
    with pytest.raises(J.JoinError, match="duplicate"):
        J.load_labels(q, expect_sha=routes.sha256(q))


def test_original_labels_load():
    rows = J.load_labels(J.RESULTS_D)
    assert len(rows) == 2730


# --- process separation -------------------------------------------------------------

GUARD_PROBE = """
import sys
sys.path.insert(0, {src!r})
import routes
routes.install_outcome_guard(writable={tmp!r})
open(routes.EGFR).read()
try:
    open({target!r}).read()
except PermissionError:
    print("REFUSED")
else:
    print("READ")
"""


@pytest.mark.parametrize("target", ["results_d.jsonl", "REPORT.md", "results_d_summary.json"])
def test_score_process_refuses_outcome_reads(tmp_path, target):
    code = GUARD_PROBE.format(src=os.path.join(RUN, "src"), tmp=str(tmp_path),
                              target=os.path.join(routes.OUTCOME_TREE, target))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    assert out.stdout.strip() == "REFUSED", out.stderr
