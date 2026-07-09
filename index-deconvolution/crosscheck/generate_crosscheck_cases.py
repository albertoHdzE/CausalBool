"""generate_crosscheck_cases.py

Emit a JSON bundle of networks and their Python-computed output repertoires so
that the canonical Wolfram reference (papers/method/code/lib/CausalBoolCore.wl)
can recompute the same repertoires and prove the Python forward model is
equivalent, gate for gate and byte for byte.

Only the gates supported by CausalBoolCore.wl are used (the full family minus
CANALISING).  KOFN parameters are exported per node.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from causalbool import repertoire
from network_generator import random_network

HERE = os.path.dirname(os.path.abspath(__file__))


def main(sizes=(6, 7, 8), seeds_per_size=15):
    cases = []
    for n in sizes:
        for seed in range(seeds_per_size):
            net = random_network(n=n, seed=5000 + seed, gate_pool="core")
            rep = repertoire(net)
            cases.append({
                "n": net.n,
                "C": net.C,
                "gates": net.gates,
                "params": net.params,  # only KOFN carries {"k": ...}
                "repertoire": rep,
            })
    path = os.path.join(HERE, "cases.json")
    with open(path, "w") as f:
        json.dump(cases, f)
    print(f"wrote {len(cases)} cases to {path}")


if __name__ == "__main__":
    main()
