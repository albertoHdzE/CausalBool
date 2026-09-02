"""generate_crosscheck_cases.py

Emit a JSON bundle of networks and their Python-computed output repertoires so
that the canonical Wolfram reference (papers/method/code/lib/CausalBoolCore.wl)
can recompute the same repertoires and prove the Python forward model is
equivalent, gate for gate and byte for byte.

AUDIT02/P1: this bundle previously used ``gate_pool="core"`` — "the full family
minus CANALISING" — because CausalBoolCore.wl had no CANALISING branch and fell
through to a silent 0.  That made the parity proof blind to precisely the gate
the downstream siblings instantiate most (12 call sites across imp-prices and
index-deconvolution).  CausalBoolCore.wl now implements all twelve families, so
the bundle uses ``gate_pool="all"`` and additionally pins the two parameters the
old bundle never exercised: KOFN ``strict`` and MAJORITY ``tiePolicy``.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from causalbool import repertoire
from network_generator import random_network

HERE = os.path.dirname(os.path.abspath(__file__))


def _pin_parameter_variants(net, variant):
    """Force the two parameters the pre-AUDIT02 bundle never exercised.

    variant 0 leaves the generator's own parameters untouched; variants 1 and 2
    additionally pin KOFN ``strict`` and MAJORITY ``tiePolicy`` respectively, so
    both branches of each are transmitted to the Wolfram side.
    """
    if variant == 0:
        return net.params
    params = [dict(p) if p else {} for p in net.params]
    for node, gate in enumerate(net.gates):
        if variant == 1 and gate == "KOFN":
            params[node]["strict"] = True
        if variant == 2 and gate == "MAJORITY":
            params[node]["tiePolicy"] = "atOrAbove"
    return params


def main(sizes=(6, 7, 8), seeds_per_size=15):
    cases = []
    for n in sizes:
        for seed in range(seeds_per_size):
            for variant in (0, 1, 2):
                net = random_network(n=n, seed=5000 + seed, gate_pool="all")
                net.params = _pin_parameter_variants(net, variant)
                rep = repertoire(net)
                cases.append({
                    "n": net.n,
                    "C": net.C,
                    "gates": net.gates,
                    "params": net.params,
                    "paramVariant": variant,
                    "repertoire": rep,
                })
    path = os.path.join(HERE, "cases.json")
    with open(path, "w") as f:
        json.dump(cases, f)
    print(f"wrote {len(cases)} cases to {path}")


if __name__ == "__main__":
    main()
