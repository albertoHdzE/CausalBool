#!/usr/bin/env python
"""C29 machinery: the density-matched BDM null, committed and pinned (AUDIT01/T2.2).

FINDINGS C29 / bitacora 07 section 1 quote a random-null result that existed only
in prose when this script was written:

    Random 14 x 14 matrices give BDM 189.39 +/- 22.75 at 17 edges and
    214.83 +/- 17.40 at 23 edges; +21.82 of the reported +33.08-bit difference
    is edge count (66 per cent); gate 156.45 sits at z = -3.35 and CPT 123.37
    at z = -2.90 against their own-density nulls.

No committed code computed those numbers. This script re-implements the null
from scratch with everything pinned, and compares elementwise against the prose.

Null design. The observed objects (phase1b connectivity matrices) are DIRECTED
zero-diagonal 14x14 adjacency matrices, edges = matrix sum. The primary null
therefore places k ones uniformly over the 182 off-diagonal cells. Because the
original session's generator was not recorded, three further candidate samplers
are reported as sensitivity: uniform placement over all 196 cells (diagonal
allowed), strict-upper-triangular placement (91 cells, DAG-shaped), and
unconditioned Bernoulli at matched expected density.

Observed anchors are taken from the committed artifact
results/phase1b_gate_network.json (panel/thermometer): bdm_gate 156.449 at 23
edges, bdm_cpt 123.368 at 17 edges, difference 33.081.

Determinism: numpy PCG64 via default_rng; seed 42 drives the primary
off-diagonal null, 43/44/45 the three sensitivity samplers; N draws per cell.

Run:
    .venv/bin/python experiments/c29_density_matched_null.py [--draws N]
Output:
    results/c29_density_matched_null.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from imp_prices.algorithmic import bdm_bits  # noqa: E402

RESULTS = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "results")

OBSERVED = dict(bdm_gate=156.449, edges_gate=23,
                bdm_cpt=123.368, edges_cpt=17, difference=33.081)

PROSE = {
    "mean_17": 189.39, "sd_17": 22.75,
    "mean_23": 214.83, "sd_23": 17.40,
    "density_share_bits": 21.82, "density_share_pct": 66.0,
    "z_gate": -3.35, "z_cpt": -2.90,
}

OFFDIAG = [(i, j) for i in range(14) for j in range(14) if i != j]
TRIU = [(i, j) for i in range(14) for j in range(14) if i < j]


def sample_exact_k(rng, cells, k, n):
    """Uniform k-subsets of `cells` (per matrix, without replacement)."""
    rows = np.array([c[0] for c in cells])
    cols = np.array([c[1] for c in cells])
    out = np.zeros((n, 14, 14), dtype=int)
    for m in range(n):
        pick = rng.choice(len(cells), size=k, replace=False)
        out[m][rows[pick], cols[pick]] = 1
    return out


def null_stats(matrices):
    vals = np.array([bdm_bits(m) for m in matrices])
    return dict(mean=round(float(vals.mean()), 2),
                sd=round(float(vals.std(ddof=1)), 2),
                n=len(vals))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=20000)
    args = ap.parse_args()
    n = args.draws

    rng = np.random.default_rng(42)
    out = {"config": {"draws_per_null": n, "seed": 42, "shape": [14, 14],
                      "primary_sampler": "exact-k uniform over 182 off-diagonal cells"},
           "observed": OBSERVED, "prose": PROSE}

    samplers = {}
    for k in (17, 23):
        s = {}
        m = sample_exact_k(np.random.default_rng(42), OFFDIAG, k, n)
        s["offdiag_182"] = null_stats(m)
        m = sample_exact_k(np.random.default_rng(43), [(i, j) for i in range(14)
                                                       for j in range(14)], k, n)
        s["diag196"] = null_stats(m)
        m = sample_exact_k(np.random.default_rng(44), TRIU, k, n)
        s["upper_tri_91"] = null_stats(m)
        g = np.random.default_rng(45)
        u = g.random((n, 14, 14))
        mm = (u < k / 196.0).astype(int)
        st = null_stats(mm)
        st["mean_edges_actual"] = round(float(mm.sum(axis=(1, 2)).mean()), 2)
        s["bernoulli_p_matched"] = st
        samplers[f"k={k}"] = s
    out["samplers"] = samplers

    # Primary-null inference, compared against the prose.
    prim17 = samplers["k=17"]["offdiag_182"]
    prim23 = samplers["k=23"]["offdiag_182"]
    share_bits = round(prim23["mean"] - prim17["mean"], 2)
    share_pct = round(100.0 * share_bits / OBSERVED["difference"], 1)
    z_gate = round((OBSERVED["bdm_gate"] - prim23["mean"]) / prim23["sd"], 2)
    z_cpt = round((OBSERVED["bdm_cpt"] - prim17["mean"]) / prim17["sd"], 2)
    primary = dict(mean_17=prim17["mean"], sd_17=prim17["sd"],
                   mean_23=prim23["mean"], sd_23=prim23["sd"],
                   density_share_bits=share_bits, density_share_pct=share_pct,
                   z_gate=z_gate, z_cpt=z_cpt)

    def classify(computed, quoted, tol_abs, tol_rel=0.02):
        if abs(computed - quoted) <= tol_abs:
            return "MATCH"
        if abs(computed - quoted) <= tol_rel * max(abs(quoted), 1e-9):
            return "CLOSE"
        return "DIVERGENT"

    comparison = {}
    for key, tol in (("mean_17", 0.01), ("sd_17", 0.01), ("mean_23", 0.01),
                     ("sd_23", 0.01), ("density_share_bits", 0.01),
                     ("z_gate", 0.005), ("z_cpt", 0.005)):
        comparison[key] = dict(prose=PROSE[key], recomputed=primary[key],
                               verdict=classify(primary[key], PROSE[key],
                                                tol_abs=tol,
                                                tol_rel=0.05 if key.startswith("sd")
                                                or key == "density_share_pct"
                                                else 0.02))
    comparison["density_share_pct"] = dict(prose=PROSE["density_share_pct"],
                                           recomputed=share_pct,
                                           verdict=classify(share_pct, 66.0,
                                                            tol_abs=0.01, tol_rel=0.075))
    out["primary_vs_prose"] = comparison

    # Robustness: does the CONCLUSION survive every candidate sampler?
    robust = []
    for name17, s17 in samplers["k=17"].items():
        s23 = samplers["k=23"][name17]
        sb = round(s23["mean"] - s17["mean"], 2)
        zg = round((OBSERVED["bdm_gate"] - s23["mean"]) / s23["sd"], 2)
        zc = round((OBSERVED["bdm_cpt"] - s17["mean"]) / s17["sd"], 2)
        robust.append(dict(sampler=name17, share_bits=sb,
                           share_pct=round(100 * sb / OBSERVED["difference"], 1),
                           z_gate=zg, z_cpt=zc))
    out["conclusion_robustness"] = robust

    divergences = [k for k, v in comparison.items() if v["verdict"] != "MATCH"]
    out["verdict"] = ("ALL-MATCH" if not divergences
                      else f"DIVERGENT: {', '.join(divergences)} "
                           "(see AUDIT_FIXING_PLAN_01 Appendix D DEV-2.2)")
    print(json.dumps(out["primary_vs_prose"], indent=2))
    print("robustness across samplers:")
    for r in robust:
        print(f"  {r['sampler']:<18} share={r['share_pct']:>5}% "
              f"z_gate={r['z_gate']} z_cpt={r['z_cpt']}")
    print("VERDICT:", out["verdict"])

    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "c29_density_matched_null.json"), "w") as fh:
        json.dump(out, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
