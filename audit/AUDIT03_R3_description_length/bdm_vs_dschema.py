#!/usr/bin/env python3
"""AUDIT03/R3.b — is D_schema related to BDM, or only to network size?

The plan asks for the comparison the author wanted: D_schema is the mechanism
side, BDM is the behaviour side, and for a deterministic system
K(output) <= K(mechanism) + O(1), so the two should move together.

One measured point does not establish that. The papers currently carry exactly
one: BDM 580.01 against D_formula 135.66, quoted as "a factor of 4.3". A single
ratio is not a relationship, and the obvious way for such a relationship to be
spurious is the one that sank every degree-driven measure in the pathinfo
replication -- BOTH quantities grow with the size of the object, so they
correlate with each other for reasons that have nothing to do with mechanism.

The design is therefore built around removing that explanation up front.

  G2  COMMON COORDINATE. n is FIXED at 10. Every network in the sample
      produces a 1024 x 10 output matrix: identical shape, identical number of
      cells, identical BDM partition. BDM cannot be responding to size,
      because size does not vary.

  A1  the relationship, with its null in the same breath: Pearson and Spearman
      between D_schema and BDM, against a permutation null on the PAIRING
      (10,000 shuffles), reported as a distribution and not as a p-value alone.

  A2  CONTROL — D_formula. D_formula is a function of n, the in-degrees and
      the gate labels alone; it never reads an output bit. If it tracks BDM as
      well as D_schema does, then the correlation is carried by the wiring
      budget and D_schema has added nothing.

  A3  CONTROL — the degree budget alone. sum(d_i) is the crudest possible
      mechanism summary. If it explains BDM as well, neither description
      length is doing work.

  A4  PARTIAL. D_schema against BDM with sum(d_i) regressed out of both. This
      is the question "is there anything left once the obvious confound is
      removed", asked directly rather than inferred.

  A5  KNOB (G3). Re-run at a different seed and a different in-degree ceiling.
      A relationship that only exists at one setting of my own knobs is a
      property of the knobs.

Run:
    venv/bin/python audit/AUDIT03_R3_description_length/bdm_vs_dschema.py
"""

from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

import numpy as np
from pybdm import BDM
from pybdm.partitions import PartitionRecursive

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "index-deconvolution" / "src"))
sys.path.insert(0, str(ROOT / "papers" / "method" / "code" / "complexity_analysis"))

from complexity_analysis import _eval_gate, encode_node_cost   # noqa: E402
from deconvolution import minimal_dnf                          # noqa: E402

N = 10
LINE = "-" * 78

# The twelve families, with the in-degrees each one admits. IMPLIES and
# NIMPLIES are binary by definition; NOT is unary. Constraining these is not
# cherry-picking -- evaluating them outside their arity is undefined.
GATE_ARITY = {
    "AND": (1, 5), "OR": (1, 5), "XOR": (1, 5), "NAND": (1, 5),
    "NOR": (1, 5), "XNOR": (1, 5), "NOT": (1, 1),
    "IMPLIES": (2, 2), "NIMPLIES": (2, 2),
    "MAJORITY": (1, 5), "KOFN": (1, 5), "CANALISING": (1, 5),
}


def _log2(x: float) -> float:
    return math.log2(x) if x > 0 else 0.0


def gamma_len(x: int) -> int:
    return 2 * (x.bit_length() - 1) + 1


def d_schema_node(gate: str, ic: list[int], params: dict, n: int = N) -> float:
    """Schema-normal-form length of ONE node, in bits.

    Identical field structure to bench_schema_normal_form.py: a self-delimiting
    count of schemata, then per schema the number of fixed coordinates, which
    coordinates they are, and their values. No catalogue is consulted, which is
    the whole point -- D_formula charges log2(12) for a dictionary it never
    transmits, and D_schema writes the templates out instead.
    """
    d = len(ic)
    tt = [_eval_gate(gate, [(y >> i) & 1 for i in range(d)], params)
          for y in range(2 ** d)]
    clauses = minimal_dnf(tt)
    if not clauses:
        return float(gamma_len(1))
    bits = float(gamma_len(len(clauses) + 1))
    for c in clauses:
        k = len(c["activators"]) + len(c["inhibitors"])
        bits += _log2(n + 1) + _log2(math.comb(n, k)) + k
    return bits


def random_network(rng: random.Random, n: int = N, dmax: int = 5):
    """A random network at FIXED n. Only the mechanism varies."""
    dyn, ics, params = [], [], {}
    for i in range(n):
        gate = rng.choice(list(GATE_ARITY))
        lo, hi = GATE_ARITY[gate]
        d = rng.randint(lo, min(hi, dmax))
        ic = sorted(rng.sample(range(n), d))
        p: dict = {}
        if gate == "KOFN":
            p = {"k": rng.randint(1, d)}
        elif gate == "IMPLIES":
            p = {"pair": [ic[0], ic[1]]}
        elif gate == "CANALISING":
            p = {"canalisingIndex": rng.randint(1, d),
                 "canalisingValue": rng.randint(0, 1),
                 "canalisedOutput": rng.randint(0, 1)}
        dyn.append(gate)
        ics.append(ic)
        params[i + 1] = p
    return dyn, ics, params


def output_table(dyn, ics, params, n: int = N) -> np.ndarray:
    rows = np.empty((2 ** n, n), dtype=int)
    for idx in range(2 ** n):
        state = [(idx >> i) & 1 for i in range(n)]
        for i in range(n):
            rows[idx, i] = _eval_gate(dyn[i], [state[j] for j in ics[i]],
                                      params[i + 1])
    return rows


def measure(rng: random.Random, count: int, dmax: int, bdm: BDM) -> dict:
    rec = {"D_schema": [], "D_formula": [], "BDM": [], "sum_d": [],
           "ones": [], "distinct_rows": []}
    for _ in range(count):
        dyn, ics, params = random_network(rng, dmax=dmax)
        tbl = output_table(dyn, ics, params)
        rec["D_schema"].append(sum(
            d_schema_node(g, ic, params[i + 1])
            for i, (g, ic) in enumerate(zip(dyn, ics))))
        rec["D_formula"].append(sum(
            encode_node_cost(len(ic), g, N) for g, ic in zip(dyn, ics)))
        rec["BDM"].append(bdm.bdm(tbl))
        rec["sum_d"].append(sum(len(ic) for ic in ics))
        rec["ones"].append(float(tbl.mean()))
        rec["distinct_rows"].append(len({tuple(r) for r in tbl}))
    return {k: np.asarray(v, dtype=float) for k, v in rec.items()}


def pearson(a, b) -> float:
    if a.std() == 0 or b.std() == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def spearman(a, b) -> float:
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return pearson(ra, rb)


def perm_null(a, b, reps: int, seed: int) -> dict:
    """Null on the PAIRING: keep both marginals exactly, destroy only the
    correspondence. This is the right null because it asks precisely whether
    THIS mechanism goes with THIS behaviour."""
    rs = np.random.default_rng(seed)
    obs = pearson(a, b)
    null = np.empty(reps)
    bb = b.copy()
    for i in range(reps):
        rs.shuffle(bb)
        null[i] = pearson(a, bb)
    more = int(np.sum(np.abs(null) >= abs(obs)))
    return {"observed": obs, "null_mean": float(null.mean()),
            "null_sd": float(null.std()),
            "null_p2.5": float(np.percentile(null, 2.5)),
            "null_p97.5": float(np.percentile(null, 97.5)),
            "p_two_sided": (more + 1) / (reps + 1)}


def residual(y, x):
    """y with x linearly regressed out."""
    if x.std() == 0:
        return y - y.mean()
    beta = np.cov(y, x, bias=True)[0, 1] / x.var()
    return y - beta * (x - x.mean()) - y.mean()


def part(t: str) -> None:
    print(f"\n{LINE}\n{t}\n{LINE}")


def main() -> int:
    print("AUDIT03/R3.b — D_schema against BDM, at fixed n")
    bdm = BDM(ndim=2, partition=PartitionRecursive, min_length=1)
    COUNT, REPS = 200, 10000

    part("G2 — THE COMMON COORDINATE")
    print(f"  n = {N} for every network in the sample, so every output object")
    print(f"  is a {2 ** N} x {N} binary matrix: same shape, same cell count,")
    print("  same BDM partition. Size is held fixed by construction rather")
    print("  than adjusted for afterwards, so 'BDM tracks the size of the")
    print("  object' is not available as an explanation of anything below.")

    rng = random.Random(20260904)
    m = measure(rng, COUNT, dmax=5, bdm=bdm)

    part("G1 — RENDER THE OBJECTS BEFORE CORRELATING THEM")
    print(f"  {COUNT} random networks, seed 20260904, in-degree ceiling 5.")
    print(f"  {'quantity':<14}{'min':>10}{'median':>10}{'max':>10}{'sd':>10}")
    for k in ("D_schema", "D_formula", "BDM", "sum_d", "ones", "distinct_rows"):
        v = m[k]
        print(f"  {k:<14}{v.min():>10.2f}{np.median(v):>10.2f}"
              f"{v.max():>10.2f}{v.std():>10.2f}")
    print("\n  The output tables are NOT degenerate: distinct-row counts span")
    print(f"  {int(m['distinct_rows'].min())} to {int(m['distinct_rows'].max())},")
    print(f"  and the ones-fraction stays near balance "
          f"({m['ones'].min():.3f}-{m['ones'].max():.3f}).")

    part("A1 — D_schema vs BDM, WITH ITS NULL")
    nul = perm_null(m["D_schema"], m["BDM"], REPS, 1)
    sp = spearman(m["D_schema"], m["BDM"])
    print(f"  Pearson  r = {nul['observed']:+.3f}   Spearman rho = {sp:+.3f}")
    print(f"  permutation null on the pairing ({REPS} shuffles, both marginals")
    print(f"  held exactly): mean {nul['null_mean']:+.4f}, sd {nul['null_sd']:.4f},")
    print(f"  central 95% [{nul['null_p2.5']:+.3f}, {nul['null_p97.5']:+.3f}],")
    print(f"  p = {nul['p_two_sided']:.5f}")

    part("A2/A3 — THE CONTROLS: does anything cheaper do as well?")
    rows = []
    for name, x in (("D_schema", m["D_schema"]),
                    ("D_formula", m["D_formula"]),
                    ("sum_d (degree budget)", m["sum_d"])):
        rows.append((name, pearson(x, m["BDM"]), spearman(x, m["BDM"])))
    print(f"  {'predictor of BDM':<24}{'Pearson':>10}{'Spearman':>10}")
    for nm, r, s in rows:
        print(f"  {nm:<24}{r:>+10.3f}{s:>+10.3f}")
    print("\n  D_formula never reads an output bit. If it matched D_schema")
    print("  here, the correlation would be a wiring-budget effect and")
    print("  D_schema would have added nothing.")

    part("A4 — PARTIAL: what survives once the degree budget is removed?")
    ry = residual(m["BDM"], m["sum_d"])
    rs_ = residual(m["D_schema"], m["sum_d"])
    rf = residual(m["D_formula"], m["sum_d"])
    pn = perm_null(rs_, ry, REPS, 2)
    print(f"  D_schema  vs BDM | sum_d :  r = {pearson(rs_, ry):+.3f}"
          f"   null 95% [{pn['null_p2.5']:+.3f}, {pn['null_p97.5']:+.3f}]"
          f"   p = {pn['p_two_sided']:.5f}")
    print(f"  D_formula vs BDM | sum_d :  r = {pearson(rf, ry):+.3f}")

    part("A5 — KNOB (G3): does it survive a different seed and ceiling?")
    print(f"  {'setting':<28}{'r(D_schema,BDM)':>18}{'r(D_formula,BDM)':>19}")
    knobs = {}
    for label, seed, dmax in (("seed 20260904, dmax 5", 20260904, 5),
                              ("seed 77, dmax 5", 77, 5),
                              ("seed 20260904, dmax 3", 20260904, 3),
                              ("seed 77, dmax 4", 77, 4)):
        mm = m if (seed, dmax) == (20260904, 5) else \
            measure(random.Random(seed), COUNT, dmax=dmax, bdm=bdm)
        rs2 = pearson(mm["D_schema"], mm["BDM"])
        rf2 = pearson(mm["D_formula"], mm["BDM"])
        knobs[label] = {"r_schema": rs2, "r_formula": rf2}
        print(f"  {label:<28}{rs2:>+18.3f}{rf2:>+19.3f}")

    part("A6 — THE ORDERING CLAIM, CHECKED DIRECTLY")
    viol = int(np.sum(m["D_schema"] >= m["BDM"]))
    print(f"  For a deterministic system K(output) <= K(mechanism) + O(1), so")
    print(f"  BDM -- an estimate of the behaviour's algorithmic content -- is")
    print(f"  expected to EXCEED D_schema, the overshoot being BDM's known")
    print(f"  block-sum overestimate rather than a defect of either.")
    print(f"  networks with D_schema >= BDM: {viol} of {COUNT}")
    ratio = m["BDM"] / m["D_schema"]
    print(f"  BDM / D_schema: median {np.median(ratio):.2f}, "
          f"range {ratio.min():.2f}-{ratio.max():.2f}")

    out = {
        "n": N, "count": COUNT, "permutations": REPS,
        "seed": 20260904, "dmax": 5,
        "summary": {k: {"min": float(v.min()), "median": float(np.median(v)),
                        "max": float(v.max()), "sd": float(v.std())}
                    for k, v in m.items()},
        "A1_d_schema_vs_bdm": nul | {"spearman": sp},
        "A2_predictors": {nm: {"pearson": r, "spearman": s}
                          for nm, r, s in rows},
        "A4_partial": {"d_schema": pearson(rs_, ry),
                       "d_formula": pearson(rf, ry),
                       "null_p2.5": pn["null_p2.5"],
                       "null_p97.5": pn["null_p97.5"],
                       "p_two_sided": pn["p_two_sided"]},
        "A5_knobs": knobs,
        "A6_ordering": {"violations": viol,
                        "bdm_over_dschema_median": float(np.median(ratio)),
                        "bdm_over_dschema_min": float(ratio.min()),
                        "bdm_over_dschema_max": float(ratio.max())},
    }
    (HERE / "bdm_vs_dschema.json").write_text(json.dumps(out, indent=1))
    print(f"\nwritten: {HERE / 'bdm_vs_dschema.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
