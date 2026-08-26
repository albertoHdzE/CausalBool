#!/usr/bin/env python3
"""Mirror test: independent Python transcription of Integration`Gates` semantics
(Gates.m Private section, transcribed verbatim) asserted ELEMENTWISE against the
WL-emitted catalogue (catalogue_from_gates.json) over every mechanism x all
2^|support|-role inputs. Exit 0 only on full equality.

This is the authority chain for R4 envelope arithmetic: Python consumers may
only use mechanisms this test proves identical to ApplyGate."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAT = HERE.parent / "experiments" / "r4_segmented_grammar" / "catalogue_from_gates.json"


# --- independent transcription of Gates.m Private semantics ---
def m_and(L): return 1 if 0 not in L else 0
def m_or(L): return 1 if 1 in L else 0
def m_xor(L): return sum(L) % 2
def m_nand(L): return 1 if 0 in L else 0
def m_nor(L): return 1 if 1 not in L else 0
def m_xnor(L): return 1 - (sum(L) % 2)
def m_not(L): return 1 - L[0]
def m_implies(L): return m_or([1 - L[0], L[1]])
def m_nimplies(L): return m_and([L[0], 1 - L[1]])


def m_majority(L, params):
    d = len(L)
    th = d // 2 + 1 if params.get("tiePolicy", "strict") != "atOrAbove" else -(-d // 2)
    return 1 if sum(L) >= th else 0


def m_kofn(L, params):
    k = params["k"]
    ones = sum(L)
    return (1 if ones > k else 0) if params.get("strict", False) else (1 if ones >= k else 0)


def m_canalising(L, params):
    i = params.get("canalisingIndex", 1)
    v = params.get("canalisingValue", 1)
    out = params.get("canalisedOutput", 0)
    return out if L[i - 1] == v else m_or(L)


PY = {"AND": m_and, "OR": m_or, "XOR": m_xor, "NAND": m_nand, "NOR": m_nor,
      "XNOR": m_xnor, "NOT": m_not, "IMPLIES": m_implies,
      "NIMPLIES": m_nimplies, "MAJORITY": m_majority, "KOFN": m_kofn,
      "CANALISING": m_canalising}


def inputs_for_w(w, lags):
    b1, b2, b3 = w & 1, (w >> 1) & 1, (w >> 2) & 1
    return [{1: b1, 2: b2, 3: b3}[l] for l in lags]


def main():
    cat = json.loads(CAT.read_text())
    fails = []
    for m in cat["mechanisms"]:
        fam, lags, tt = m["family"], m["support"], m["tt"]
        f = PY[fam]
        for w in range(8):
            L = inputs_for_w(w, lags)
            py_val = f(L, dict(m["params"])) if fam in ("MAJORITY", "KOFN", "CANALISING") \
                else f(L)
            if py_val != tt[w]:
                fails.append((fam, m["params"], lags, w, tt[w], py_val))
    n_const = sum(1 for m in cat["mechanisms"] if m["constant"])
    # constant flags must agree with the TT itself
    for m in cat["mechanisms"]:
        if (len(set(m["tt"])) == 1) != bool(m["constant"]):
            fails.append((m["family"], m["params"], m["support"], "CONSTFLAG", None, None))
    print(f"mechanisms checked: {len(cat['mechanisms'])} "
          f"(constant-flagged {n_const}) x 8 inputs each")
    if fails:
        print(f"MIRROR FAILURES: {len(fails)}")
        for f_ in fails[:10]:
            print("  ", f_)
        sys.exit(1)
    print("MIRROR OK: Python transcription == ApplyGate elementwise, all mechanisms")
    sys.exit(0)


if __name__ == "__main__":
    main()
