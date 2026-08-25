"""exp07_reprogramming.py

Exact network reprogramming with the index method, compared face to face with
the approximate BDM reprogramming of Zenil and colleagues, on real
gene-regulatory networks.

Ours: perturb each node (knockout) and measure the exact change in the dynamics
(image size and attractor count).  Zenil's: perturb each node and measure the
change in the BDM of the adjacency matrix.  The two spectra are compared by rank
correlation.  Ours is exact and dynamical; Zenil's is approximate and structural.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from bnet import parse_bnet
from reprogramming import (image_size, num_attractors, spectrum,
                           relative_reprogrammability)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BNET_DIR = os.path.join(ROOT, "data", "bio", "raw")
RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
CROSS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "crosscheck")
IMP_PY = os.path.join(ROOT, "imp-causal-paper", ".venv", "bin", "python")

MODELS = [
    ("Arabidopsis root stem cell", "pyboolnet_arellano_rootstem.bnet"),
    ("Fission yeast cell cycle", "pyboolnet_davidich_yeast.bnet"),
    ("Mammalian cell cycle", "pyboolnet_faure_cellcycle.bnet"),
    ("IRMA synthetic yeast", "pyboolnet_irma.bnet"),
    ("Myeloid differentiation", "pyboolnet_krumsiek_myeloid.bnet"),
    ("Apoptosis", "pyboolnet_tournier_apoptosis.bnet"),
    ("WNT5A melanoma", "pyboolnet_xiao_wnt5a.bnet"),
]
MAX_N = 14


def _spearman(a, b):
    def rank(xs):
        order = sorted(range(len(xs)), key=lambda i: xs[i])
        r = [0.0] * len(xs)
        i = 0
        while i < len(xs):
            j = i
            while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
                j += 1
            avg = (i + j) / 2.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    ra, rb = rank(a), rank(b)
    n = len(a)
    ma = sum(ra) / n
    mb = sum(rb) / n
    cov = sum((ra[i] - ma) * (rb[i] - mb) for i in range(n))
    va = sum((ra[i] - ma) ** 2 for i in range(n)) ** 0.5
    vb = sum((rb[i] - mb) ** 2 for i in range(n)) ** 0.5
    return cov / (va * vb) if va > 0 and vb > 0 else 0.0


def run():
    records = []
    adjacency = {}
    for label, fname in MODELS:
        path = os.path.join(BNET_DIR, fname)
        if not os.path.exists(path):
            continue
        net, names = parse_bnet(path)
        if net.n > MAX_N:
            continue
        info_img = spectrum(net, image_size)
        info_attr = spectrum(net, num_attractors)
        pr = relative_reprogrammability(info_img)
        adjacency[label] = net.C
        order = sorted(range(net.n), key=lambda i: -abs(info_img[i]))
        top = [(names[i], info_img[i]) for i in order[:3]]
        records.append({"label": label, "n": net.n, "names": names,
                        "info_image": info_img, "info_attractors": info_attr,
                        "relative_reprogrammability": pr, "top3": top})
        print(f"{label:30s} n={net.n:2d}  Pr={pr:.2f}  "
              f"top reprogrammable: {', '.join(f'{g}({v:+d})' for g, v in top)}")

    # Zenil BDM spectra via the imp-causal-paper environment
    adj_path = os.path.join(CROSS, "reprog_adjacency.json")
    bdm_path = os.path.join(CROSS, "reprog_bdm.json")
    with open(adj_path, "w") as f:
        json.dump(adjacency, f)
    bdm_spectra = {}
    if os.path.exists(IMP_PY):
        try:
            subprocess.run([IMP_PY, os.path.join(CROSS, "zenil_bdm_spectrum.py"),
                            adj_path, bdm_path], check=True, capture_output=True)
            bdm_spectra = json.load(open(bdm_path))
        except Exception as exc:  # noqa: BLE001
            print(f"BDM step skipped: {exc}")
    else:
        print("imp-causal-paper venv not found; skipping BDM comparison")

    print("\n=== face-to-face: ours (exact dynamics) vs Zenil (BDM topology) ===")
    comparisons = []
    for rec in records:
        z = bdm_spectra.get(rec["label"])
        if not z:
            continue
        rho = _spearman(rec["info_image"], z)
        comparisons.append({"label": rec["label"], "spearman_image_vs_bdm": rho})
        print(f"  {rec['label']:30s} Spearman(our image-info, Zenil BDM-info) = {rho:+.3f}")

    summary = {"experiment": "reprogramming", "records": records,
               "comparisons": comparisons}
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp07_reprogramming.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("\nwritten: results/exp07_reprogramming.json")
    return summary


if __name__ == "__main__":
    run()
