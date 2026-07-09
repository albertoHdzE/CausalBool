"""exp03_ca_to_network.py

Deconvolve elementary cellular-automaton space-time diagrams into Boolean
networks and verify the recovered network reproduces the diagram.  Uses the same
rules that appear in the imp-causal-paper reproduction (Zenil et al. 2019).

For each rule the script generates a diagram from a random initial condition
wide and long enough to exhibit every local neighbourhood, deconvolves it with
the original hidden, and reports the recovered local gate, the functional
support, the neighbourhood coverage, and whether the network reproduces the
diagram exactly.
"""

from __future__ import annotations

import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from ca_deconvolution import evolve_eca, deconvolve_ca, verify_ca

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")

# Rules featured in the paper reproduction plus a few with named-gate identities.
RULES = [254, 90, 30, 110, 232, 204, 250, 150, 170, 57, 45, 73]

# Expected named-gate identity where one exists (for commentary only).
KNOWN_IDENTITY = {
    254: "OR (l,c,r)", 90: "XOR (l,r); centre irrelevant",
    232: "MAJORITY (l,c,r)", 204: "identity (centre)",
    170: "shift (right)", 150: "XOR (l,c,r)", 250: "OR (l,r); centre irrelevant",
}


def run(width=12, steps=10, n_ic=80, seed0=1):
    """Deconvolve each rule from an ensemble of ``n_ic`` random initial
    conditions, wide and numerous enough to observe every local neighbourhood,
    then verify exact global-map recovery (not merely trajectory reproduction).
    """
    records = []
    n_traj_exact = 0
    n_global_exact = 0
    for rule in RULES:
        rng = random.Random(seed0 + rule)
        diagrams = [
            evolve_eca(rule, [rng.randint(0, 1) for _ in range(width)], steps)
            for _ in range(n_ic)
        ]

        net, reports = deconvolve_ca(diagrams, max_radius=3)
        vr = verify_ca(diagrams, net, rule=rule)
        if vr["trajectory_exact"]:
            n_traj_exact += 1
        if vr.get("global_map_exact"):
            n_global_exact += 1

        rep = reports[width // 2]  # interior cell as representative local rule
        min_cov = min(r.coverage for r in reports)
        rec = {
            "rule": rule,
            "trajectory_exact": vr["trajectory_exact"],
            "global_map_exact": vr.get("global_map_exact"),
            "interior_support_size": len(rep.support),
            "interior_gate": rep.canonical.as_dict(),
            "min_coverage": min_cov,
            "known_identity": KNOWN_IDENTITY.get(rule, "no canonical name"),
        }
        records.append(rec)
        print(f"rule {rule:3d}: global_exact={str(vr.get('global_map_exact')):5s} "
              f"traj_exact={str(vr['trajectory_exact']):5s} "
              f"support={len(rep.support)} gate={rep.canonical.gate:>9s} "
              f"min_cov={min_cov:.2f}  [{KNOWN_IDENTITY.get(rule, 'no canonical name')}]")

    summary = {
        "experiment": "ca_to_network",
        "width": width, "steps": steps, "n_ic": n_ic, "rules": RULES,
        "n_rules": len(RULES), "n_trajectory_exact": n_traj_exact,
        "n_global_map_exact": n_global_exact, "records": records,
    }
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp03_ca_to_network.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\ntrajectory exact : {n_traj_exact}/{len(RULES)} rules")
    print(f"global map exact : {n_global_exact}/{len(RULES)} rules")
    print("written: results/exp03_ca_to_network.json")
    return summary


if __name__ == "__main__":
    run()
