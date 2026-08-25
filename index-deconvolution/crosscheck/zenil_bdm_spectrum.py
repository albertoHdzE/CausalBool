"""zenil_bdm_spectrum.py

Compute Zenil's node information spectrum for a set of network adjacency
matrices: info(node) = BDM(A) - BDM(A without node), the change in the
approximate algorithmic complexity (block decomposition method) of the adjacency
matrix when the node is deleted.  This is the method of Zenil and colleagues.

Run with the imp-causal-paper virtual environment, which provides pybdm:
    imp-causal-paper/.venv/bin/python zenil_bdm_spectrum.py in.json out.json
"""

import json
import sys
import warnings

import numpy as np
from pybdm import BDM

warnings.filterwarnings("ignore")


def main(in_path, out_path):
    bdm = BDM(ndim=2, warn_if_missing_ctm=False)
    data = json.load(open(in_path))
    out = {}
    for label, C in data.items():
        A = np.array(C, dtype=int)
        n = A.shape[0]
        try:
            base = bdm.bdm(A)
            info = []
            for k in range(n):
                A2 = np.delete(np.delete(A, k, axis=0), k, axis=1)
                info.append(float(base - bdm.bdm(A2)))
        except Exception as exc:  # noqa: BLE001
            info = None
            print(f"{label}: BDM failed ({exc})", file=sys.stderr)
        out[label] = info
    json.dump(out, open(out_path, "w"))
    print(f"wrote BDM spectra for {len(out)} networks")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
