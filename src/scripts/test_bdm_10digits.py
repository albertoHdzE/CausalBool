"""Scratch check of pybdm's BDM and entropy on a short 1-D sequence.

AUDIT04 Phase 2. The whole body used to run at module level, so importing this
file executed it, printed to stdout and constructed a BDM object. It is kept
because it records what was checked, but it now runs only when invoked.

Note on the name: `test_bdm_10digits.py` is NOT a pytest test and never was --
it makes no assertions. It is classified as a producer/scratch script; the
declared test manifest is tests/MUnit/MANIFEST.tsv.

Note on the sequence: `X` is np.ones(11), i.e. eleven ones, despite the title
saying "random binary sequence of 10 digits". Recorded rather than silently
corrected, because the printed value was obtained from this input.
"""
import numpy as np
from pybdm import BDM


def main() -> int:
    print("--- Test: Random Binary Sequence of 10 Digits ---")

    X = np.ones((11,), dtype=int)
    print(f"Sequence: {X}")
    print(f"Length: {len(X)}")

    print("\nInitializing BDM(ndim=1)...")
    bdm = BDM(ndim=1)

    print("\nComputing BDM(X)...")
    try:
        print(f"BDM Value: {bdm.bdm(X)}")
    except Exception as e:
        print(f"Error computing BDM: {e}")

    print("\nComputing Entropy(X)...")
    try:
        print(f"Entropy Value: {bdm.ent(X)}")
    except Exception as e:
        print(f"Error computing Entropy: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
