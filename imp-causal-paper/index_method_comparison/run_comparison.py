#!/usr/bin/env python
"""Index-method capability comparison — EXECUTION of the approved pre-registration
(imp-causal-paper/index_method_comparison/PROTOCOL.md, D-7 approved 2026-08-24).

Arms:
  CA      : the 10 ECA rules fixed by the replication's committed
            scripts/run_ca_reconstruction.py (RULES = [254,57,11,50,9,54,75,73,45,30]).
            The root project's exact engine (index-deconvolution ca_deconvolution)
            reconstructs the network from pooled space-time trajectories; the
            recovered network is verified ELEMENTWISE against the automaton's
            exhaustive global map.
  Th17    : data/processed/th17/ was EMPTY at registration -> EXCLUDED-WITH-REASON
            (no parsed Boolean networks; raw GEO series require an offline
            pipeline that does not exist in this tree). Never silently dropped.
  E. coli : data/processed/ecoli holds SIGNED INTERACTION LISTS only
            (ecoli_tf_gene_confC.txt); no Boolean update functions exist in any
            committed artifact, so no ground-truth repertoire can be constructed
            without inventing gates. -> EXCLUDED-WITH-REASON (this is itself a
            finding: the biological arms of the replication were never
            exactness-gradable; cf. V4 round-trip framing).

Determinism: numpy PCG64 rng seeded per protocol; seeds recorded in the output.
No outcome-dependent parameters: radius, widths, steps, IC counts below are fixed
constants chosen before execution and are NOT tuned per rule.

Run (from repo root):
    python imp-causal-paper/index_method_comparison/run_comparison.py
Output:
    imp-causal-paper/results/index_method_comparison/
        capability_table.md, capability_table.json, runs.json,
        MANIFEST.sha256 (verified by ../../scripts/verify_manifest.py — see
        imp-causal-paper/scripts/verify_manifest.py)
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "index-deconvolution", "src"))

from ca_deconvolution import ca_global_map, deconvolve_ca, evolve_eca  # noqa: E402
from causalbool import Network, repertoire  # noqa: E402

OUT_DIR = os.path.join(HERE, "..", "results", "index_method_comparison")

RULES = [254, 57, 11, 50, 9, 54, 75, 73, 45, 30]   # frozen by run_ca_reconstruction.py
WIDTH = 11          # fixed: global-map verification costs 2**11 x 11
STEPS = 30          # fixed trajectory length per initial condition
N_ICS = 60          # fixed number of pooled initial conditions
RADIUS = 1          # fixed: ECA neighbourhood
SEED = 42


def run_rule(rule: int) -> dict:
    rng = np.random.default_rng(SEED + rule)     # per-rule stream, seed recorded
    diagrams = []
    for _ in range(N_ICS):
        ic = [int(b) for b in rng.integers(0, 2, size=WIDTH)]
        diagrams.append(evolve_eca(rule, ic, STEPS))

    t0 = time.time()
    net, reports = deconvolve_ca(diagrams, max_radius=RADIUS)
    seconds = round(time.time() - t0, 2)

    # elementwise verification against the exhaustive global map, via the
    # engine's own canonical repertoire() instrument
    truth = ca_global_map(rule, WIDTH)
    one = Network(n=WIDTH, C=net.C, gates=net.gates, params=net.params)
    recovered = repertoire(one)

    diffs = [(x, i) for x, (t_row, r_row) in enumerate(zip(truth, recovered))
             for i, (a, b) in enumerate(zip(t_row, r_row)) if a != b]
    return dict(
        rule=rule, width=WIDTH, steps=STEPS, n_diagrams=N_ICS, seed=SEED + rule,
        cells=int(WIDTH),
        gates=[g for g in net.gates],
        edges=sum(sum(row) for row in net.C),
        global_map_rows=len(truth),
        mismatches=len(diffs),
        mismatch_locations_sample=diffs[:10],
        exact=(len(diffs) == 0),
        support_sizes=[len(r.support) for r in reports],
    )


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    started = datetime.datetime.now().isoformat(timespec="seconds")

    ca_results = [run_rule(r) for r in RULES]
    n_exact = sum(1 for r in ca_results if r["exact"])

    exclusions = [
        {"arm": "Th17",
         "reason": "data/processed/th17/ empty at registration (protocol s3): "
                   "no parsed Boolean networks committed; raw GEO series matrices "
                   "require an offline processing pipeline absent from this tree.",
         "status": "EXCLUDED-WITH-REASON"},
        {"arm": "E. coli subset",
         "reason": "committed artifacts contain signed interaction lists only "
                   "(ecoli_tf_gene_confC.txt); no Boolean update functions exist, "
                   "so a ground-truth repertoire cannot be constructed without "
                   "inventing gates (forbidden by protocol s5/no-invention). "
                   "Finding: the replication's biological arms were never "
                   "exactness-gradable ground truths.",
         "status": "EXCLUDED-WITH-REASON"},
    ]

    # volatile fields (wall-clock) deliberately excluded so that reruns are
    # byte-identical and the MANIFEST.sha256 verifies (protocol s5/determinism)
    payload = dict(
        preregistration="index_method_comparison/PROTOCOL.md (D-7 approved 2026-08-24)",
        approval_commit="2b6c5a8",
        config=dict(rules=RULES, width=WIDTH, steps=STEPS, n_ics=N_ICS,
                    radius=RADIUS, seed=SEED),
        ca_arm=ca_results,
        ca_summary=dict(n_rules=len(RULES), n_exact_global_map=n_exact,
                        total_mismatches=sum(r["mismatches"] for r in ca_results)),
        excluded_arms=exclusions,
    )
    with open(os.path.join(OUT_DIR, "runs.json"), "w") as fh:
        json.dump(payload, fh, indent=2)

    # ---- capability table, COMPARISON.md format ---------------------------
    lines = []
    lines.append("# Capability table — index method vs Zenil calculus (CA arm)")
    lines.append("")
    lines.append("Generated by `index_method_comparison/run_comparison.py` under the")
    lines.append("approved pre-registration (D-7, approved 2026-08-24, commit 2b6c5a8,")
    lines.append("pre-dating this file). Elementwise criterion: recovered network's")
    lines.append("global map equals the automaton's exhaustive map on all 2^11 x 11 cells.")
    lines.append("")
    lines.append("| rule | Wolfram class | exact global map | mismatches (of 22528 cells) | recovered edges | max support |")
    lines.append("|---|---|---|---|---|---|")
    classes = {254: "IV*", 57: "II", 11: "II", 50: "II", 9: "I",
               54: "IV", 75: "II", 73: "II", 45: "III", 30: "III"}
    for r in ca_results:
        lines.append(f"| {r['rule']} | {classes.get(r['rule'], '—')} | "
                     f"{'YES' if r['exact'] else 'NO'} | {r['mismatches']} | "
                     f"{r['edges']} | {max(r['support_sizes'])} |")
    lines.append("")
    lines.append(f"**CA summary: {n_exact}/{len(RULES)} rules exact** "
                 f"({payload['ca_summary']['total_mismatches']} mismatched cells total).")
    lines.append("")
    lines.append("| arm | status | reason |")
    lines.append("|---|---|---|")
    for e in exclusions:
        lines.append(f"| {e['arm']} | {e['status']} | {e['reason']} |")
    lines.append("")
    lines.append("Zenil-calculus side is quoted ONLY from committed replication")
    lines.append("artifacts (results/ca/summary.json: inferred_rule 222 vs true rule")
    lines.append("254 on its 6-node demo network; SESSION_HANDOFF's rho=+1.0 claim is")
    lines.append("superseded) and was not re-executed here.")
    table = "\n".join(lines) + "\n"
    with open(os.path.join(OUT_DIR, "capability_table.md"), "w") as fh:
        fh.write(table)

    # ---- manifest ---------------------------------------------------------
    manifest_lines = []
    for name in sorted(os.listdir(OUT_DIR)):
        if name == "MANIFEST.sha256":
            continue
        p = os.path.join(OUT_DIR, name)
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        manifest_lines.append(f"{h}  {name}")
    with open(os.path.join(OUT_DIR, "MANIFEST.sha256"), "w") as fh:
        fh.write("\n".join(manifest_lines) + "\n")

    print(table)
    print("manifest:", len(manifest_lines), "entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
