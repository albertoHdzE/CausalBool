"""
BDM comparison programme for the 10-node mixed-gate Boolean network.

Companion to Section 4.2 of the computational manuscript. Places the exact
description length D_formula alongside three measures of the *behaviour* it
generates, and alongside a gate-level algorithmic measure.

Experiments
-----------
  5.1  data side      -- BDM / ZIP / H_total over the 2^n x n output repertoire,
                         with a row-shuffle control and a density-matched random
                         control.
  5.2  gate side      -- BDM over truth tables at fixed arity (canonical,
                         representation-free, equal length across families).
  5.3  negative       -- two rejected binarisations, retained as worked negative
                         results because they demonstrate representation artefacts.
  5.4  mechanism side -- BDM(adjacency) vs D_wiring.

Determinism
-----------
All randomness is seeded (SEED below). Re-running reproduces every figure exactly.

Partition strategy
------------------
pybdm's default PartitionIgnore silently DISCARDS leftover columns: on a 1024 x 10
matrix with 4x4 blocks it measures only 8 of the 10 columns. Every result here uses
PartitionRecursive(min_length=...), which covers the whole object. The default is
reported alongside in 5.1 solely to document the size of the artefact.

Caveat on units and scale
-------------------------
BDM values are CTM-derived bits. They are bits under a different convention from
D_formula's code length; both are reported in bits but they are not interchangeable.
BDM is also known to converge toward Shannon entropy once blocks outrun the CTM
tables, so values at large scales should be read with that in mind.

Usage:
    python bdm_comparison.py

Outputs: bdm_results.json
"""

from __future__ import annotations

import itertools
import json
import math
import random
import zlib
from pathlib import Path

import numpy as np
from pybdm import BDM
from pybdm.partitions import PartitionIgnore, PartitionRecursive

import complexity_analysis as ca

SEED = 7

# Fixed arity at which all gate families are compared in 5.2.
GATE_ARITY = 4

# Parameters needed to instantiate the parameterised families at GATE_ARITY.
GATE_PARAMS = {
    "KOFN": {"k": 2},
    "IMPLIES": {"pair": (1, 2)},
    "NIMPLIES": {"pair": (1, 2)},
    "CANALISING": {"canalisingIndex": 1, "canalisingValue": 1, "canalisedOutput": 0},
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def zip_bits(arr: np.ndarray) -> int:
    """zlib -9 over the same CSV serialisation used by complexity_analysis."""
    csv = "".join(",".join(map(str, row)) + "\n" for row in arr.tolist()).encode("ascii")
    return len(zlib.compress(csv, 9)) * 8


def h_total_bits(arr: np.ndarray) -> float:
    """i.i.d. Shannon coding cost of the whole array, matching compute_h_total."""
    p = float(arr.mean())
    return ca._binary_entropy(p) * arr.size


# ---------------------------------------------------------------------------
# 5.1 data side
# ---------------------------------------------------------------------------

def experiment_data_side(table: np.ndarray) -> dict:
    rng = np.random.default_rng(SEED)

    shuffled = table[rng.permutation(table.shape[0])]
    random_matched = (rng.random(table.shape) < table.mean()).astype(int)

    bdm_rec = BDM(ndim=2, partition=PartitionRecursive, min_length=1)
    bdm_ign = BDM(ndim=2, partition=PartitionIgnore)

    objects = {
        "true_repertoire": table,
        "row_shuffled": shuffled,
        "random_matched": random_matched,
    }

    out = {}
    for name, arr in objects.items():
        out[name] = {
            "BDM_recursive": round(float(bdm_rec.bdm(arr)), 4),
            "BDM_ignore_default": round(float(bdm_ign.bdm(arr)), 4),
            "ZIP_bits": zip_bits(arr),
            "H_total_bits": round(h_total_bits(arr), 4),
            "ones_fraction": round(float(arr.mean()), 6),
        }

    t = out["true_repertoire"]["BDM_recursive"]
    out["separation"] = {
        "random_over_true": round(out["random_matched"]["BDM_recursive"] / t, 3),
        "shuffled_over_true": round(out["row_shuffled"]["BDM_recursive"] / t, 3),
    }
    return out


# ---------------------------------------------------------------------------
# 5.2 gate side -- truth tables at fixed arity
# ---------------------------------------------------------------------------

def truth_table(gate: str, arity: int) -> np.ndarray:
    """
    The gate's extensional definition as a 2^arity-bit vector.

    Input enumeration matches TruthTable in src/Packages/Integration/Gates.m:38,
    i.e. IntegerDigits[x, 2, arity] for x = 0 .. 2^arity - 1 (MSB-first tuples).
    """
    params = GATE_PARAMS.get(gate, {})
    rows = [ca._eval_gate(gate, list(x), params)
            for x in itertools.product([0, 1], repeat=arity)]
    return np.array(rows, dtype=int)


def experiment_gate_side(arity: int = GATE_ARITY) -> dict:
    bdm1 = BDM(ndim=1, partition=PartitionRecursive, min_length=2)
    out = {}
    for gate in ca.GATE_LABELS:
        tt = truth_table(gate, arity)
        out[gate] = {
            "truth_table": "".join(map(str, tt.tolist())),
            "ones": int(tt.sum()),
            "BDM": round(float(bdm1.bdm(tt)), 4),
        }
    return out


def check_complement_invariance(gate_results: dict) -> list:
    """
    Sanity check: complementation costs O(1) bits, so complement pairs must
    receive equal BDM. A failure here indicates the measure is responding to
    surface form rather than logical structure.
    """
    pairs = [("AND", "NAND"), ("OR", "NOR"), ("XOR", "XNOR")]
    return [(a, b, gate_results[a]["BDM"], gate_results[b]["BDM"],
             math.isclose(gate_results[a]["BDM"], gate_results[b]["BDM"]))
            for a, b in pairs]


# ---------------------------------------------------------------------------
# 5.3 rejected binarisations -- retained as worked negative results
# ---------------------------------------------------------------------------

def experiment_rejected_label_codes(n_assignments: int = 3) -> dict:
    """
    Assign each gate an arbitrary 4-bit label and run BDM over the resulting
    stream for the 10-node network.

    12 gate families require 4 bits, not 3 (2^3 = 8 < 12).

    Expected outcome: the value changes with the labelling, so the measure is of
    the code, not of the gates. This variant must not be used.
    """
    bdm1 = BDM(ndim=1, partition=PartitionRecursive, min_length=2)
    results = []
    for seed in range(1, n_assignments + 1):
        rnd = random.Random(seed)
        order = ca.GATE_LABELS[:]
        rnd.shuffle(order)
        code = {g: [int(c) for c in format(i, "04b")] for i, g in enumerate(order)}
        stream = np.array([b for g in ca.DYN10 for b in code[g]], dtype=int)
        results.append({"assignment_seed": seed, "BDM": round(float(bdm1.bdm(stream)), 4)})
    values = [r["BDM"] for r in results]
    return {
        "assignments": results,
        "spread": round(max(values) - min(values), 4),
        "verdict": "REJECTED: identical network, different labelling, different BDM",
    }


def experiment_rejected_name_ascii() -> dict:
    """
    BDM over the ASCII bits of the gate names.

    Expected outcome: BDM is essentially linear in the length of the English word,
    so the measure tracks the lexicon rather than the logic. This variant must not
    be used. Same failure mode as AOAC-vs-molecule-size in the imp-pathinfo work.
    """
    bdm1 = BDM(ndim=1, partition=PartitionRecursive, min_length=2)
    rows = []
    for gate in ca.GATE_LABELS:
        bits = np.array([int(c) for ch in gate for c in format(ord(ch), "08b")], dtype=int)
        rows.append({"gate": gate, "n_bits": int(bits.size),
                     "BDM": round(float(bdm1.bdm(bits)), 4),
                     "BDM_per_bit": round(float(bdm1.bdm(bits)) / bits.size, 4)})
    lens = np.array([r["n_bits"] for r in rows], dtype=float)
    vals = np.array([r["BDM"] for r in rows], dtype=float)
    corr = float(np.corrcoef(lens, vals)[0, 1])
    return {
        "per_gate": rows,
        "pearson_r_BDM_vs_name_length": round(corr, 6),
        "verdict": "REJECTED: measures English word length, not gate semantics",
    }


# ---------------------------------------------------------------------------
# 5.4 mechanism side
# ---------------------------------------------------------------------------

def experiment_mechanism_side() -> dict:
    cm = np.array(ca.CM10, dtype=int)
    n = len(ca.DYN10)
    bdm2 = BDM(ndim=2, partition=PartitionRecursive, min_length=1)
    d_wiring = sum(math.log2(math.comb(n, sum(row))) for row in ca.CM10)
    return {
        "BDM_adjacency": round(float(bdm2.bdm(cm)), 4),
        "ZIP_adjacency_bits": zip_bits(cm),
        "D_wiring_bits": round(d_wiring, 4),
        "note": ("Only D_wiring is comparable with BDM(cm): D_formula also encodes "
                 "gate types and parameters, which the adjacency matrix does not "
                 "contain. At 10x10 CTM-table coverage is a real concern."),
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    n = len(ca.DYN10)
    table = np.array(ca.build_output_table(ca.CM10, ca.DYN10, ca.PARAMS10), dtype=int)

    D = ca.compute_d_formula(ca.CM10, ca.DYN10, n)
    data = experiment_data_side(table)
    gates = experiment_gate_side()
    mech = experiment_mechanism_side()
    rej_codes = experiment_rejected_label_codes()
    rej_names = experiment_rejected_name_ascii()

    true_bdm = data["true_repertoire"]["BDM_recursive"]
    true_zip = data["true_repertoire"]["ZIP_bits"]
    true_h = data["true_repertoire"]["H_total_bits"]

    print("=" * 72)
    print("  BDM comparison — 10-node mixed-gate network   (seed %d)" % SEED)
    print("=" * 72)
    print()
    print("  5.1  DATA SIDE — describing the behaviour")
    print(f"  {'object':<20} {'BDM':>12} {'ZIP':>10} {'H_total':>12}")
    print("  " + "-" * 58)
    for k in ("true_repertoire", "row_shuffled", "random_matched"):
        r = data[k]
        print(f"  {k:<20} {r['BDM_recursive']:>12.2f} {r['ZIP_bits']:>10d} {r['H_total_bits']:>12.2f}")
    print()
    print(f"  D_formula (the programme)            {D:>12.2f} bits")
    print(f"  BDM / D_formula                      {true_bdm / D:>12.2f}x")
    print(f"  separation random/true (BDM)         {data['separation']['random_over_true']:>12.2f}x")
    print(f"  separation shuffled/true (BDM)       {data['separation']['shuffled_over_true']:>12.2f}x")
    print()
    print(f"  partition artefact: default PartitionIgnore drops 2 of {n} columns")
    print(f"    recursive (all columns) {data['true_repertoire']['BDM_recursive']:>10.2f}")
    print(f"    ignore    (8 columns)   {data['true_repertoire']['BDM_ignore_default']:>10.2f}")
    print()

    print(f"  5.2  GATE SIDE — truth tables at arity d={GATE_ARITY}")
    print(f"  {'gate':<12} {'truth table':<18} {'ones':>5} {'BDM':>9}")
    print("  " + "-" * 48)
    for g, r in sorted(gates.items(), key=lambda kv: -kv[1]["BDM"]):
        print(f"  {g:<12} {r['truth_table']:<18} {r['ones']:>5} {r['BDM']:>9.3f}")
    print()
    print("  complement-pair invariance (must all be True):")
    inv = check_complement_invariance(gates)
    for a, b, va, vb, ok in inv:
        print(f"    {a:<6} {va:8.3f}  vs  {b:<6} {vb:8.3f}   {ok}")
    print()

    print("  5.3  REJECTED BINARISATIONS (negative results — do not use)")
    print(f"    label codes : BDM = {[r['BDM'] for r in rej_codes['assignments']]}")
    print(f"                  spread {rej_codes['spread']:.2f} bits across arbitrary labellings")
    print(f"    name ASCII  : Pearson r(BDM, name length) = "
          f"{rej_names['pearson_r_BDM_vs_name_length']:.4f}")
    print()

    print("  5.4  MECHANISM SIDE")
    print(f"    BDM(adjacency) = {mech['BDM_adjacency']:.2f} bits")
    print(f"    D_wiring       = {mech['D_wiring_bits']:.2f} bits")
    print()

    # -----------------------------------------------------------------------
    # self-checks
    # -----------------------------------------------------------------------
    checks = [
        ("D_formula < BDM(true)", D < true_bdm),
        ("BDM(true) < ZIP(true)", true_bdm < true_zip),
        ("ZIP(true) <= H_total(true)", true_zip <= true_h),
        ("BDM separates true from random (>5x)", data["separation"]["random_over_true"] > 5.0),
        ("BDM separates true from shuffled (>5x)", data["separation"]["shuffled_over_true"] > 5.0),
        ("complement pairs invariant", all(ok for *_, ok in inv)),
        ("label codes are labelling-dependent", rej_codes["spread"] > 0.0),
        ("name ASCII tracks word length (r>0.95)",
         rej_names["pearson_r_BDM_vs_name_length"] > 0.95),
        ("all 12 gate families evaluated", len(gates) == 12),
    ]
    print("  SELF-CHECKS")
    for name, ok in checks:
        print(f"    {'PASS' if ok else 'FAIL'}  {name}")
    print()
    all_ok = all(ok for _, ok in checks)
    print(f"  Overall: {'PASS' if all_ok else 'FAIL'}")
    print("=" * 72)

    results = {
        "seed": SEED,
        "gate_arity": GATE_ARITY,
        "D_formula_bits": round(D, 5),
        "data_side": data,
        "gate_side": gates,
        "mechanism_side": mech,
        "rejected_label_codes": rej_codes,
        "rejected_name_ascii": rej_names,
        "ordering": "D_formula < BDM < ZIP ~ H_total",
        "self_checks_pass": all_ok,
    }
    out_path = Path(__file__).parent / "bdm_results.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n  Results written to {out_path.name}")


if __name__ == "__main__":
    main()
