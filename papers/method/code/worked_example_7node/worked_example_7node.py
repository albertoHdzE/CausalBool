"""
Worked example for Section 2.2: base set and offset family of a single node.

Regenerates every number quoted in Section 2.2 of the computational manuscript, so
that the example is reproducible rather than asserted. Emits a JSON summary and a
LaTeX fragment.

The subject is node 4 of the 7-node network introduced in the UNAM thesis
(Chapter 4): an AND gate reading inputs {1,3,5,7} inside a 7-node system.

Indexing
--------
Repertoire positions are reported 0-based here, matching the thesis. The manuscript
uses the index universe U_n = {1, ..., 2^n}; the two differ by one throughout, and
the LaTeX fragment emits the 1-based form.

Usage:
    python worked_example_7node.py

Outputs: worked_example_7node.json, worked_example_7node.tex
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "complexity_analysis"))
import complexity_analysis as ca  # noqa: E402

# 7-node network, thesis Chapter 4.
CM07 = [
    [0, 0, 1, 0, 0, 0, 1],
    [0, 0, 1, 0, 0, 1, 0],
    [1, 0, 0, 0, 1, 0, 1],
    [1, 0, 1, 0, 1, 0, 1],   # node 4: AND over inputs {1,3,5,7}
    [0, 0, 1, 1, 0, 1, 1],
    [1, 1, 1, 0, 0, 0, 0],
    [0, 1, 0, 1, 1, 1, 0],
]
DYN07 = ["AND", "OR", "OR", "AND", "OR", "OR", "AND"]

NODE = 4          # 1-based


def isolated_output(cm, dyn, node0, params=None):
    """The node's output across the whole ordered repertoire, LSB-first."""
    n = len(dyn)
    params = params or {}
    ics = [j for j, v in enumerate(cm[node0]) if v == 1]
    out = []
    for idx in range(2 ** n):
        state = [(idx >> i) & 1 for i in range(n)]
        out.append(ca._eval_gate(dyn[node0], [state[j] for j in ics],
                                 params.get(node0 + 1, {})))
    return out


def base_and_offsets(cm, dyn, node0, params=None, value=1):
    """
    Base set L and offset family Omega.

    L : positions where the node takes `value` when only its connected inputs vary
        and every disconnected coordinate is held at zero.
    Omega : all subset sums of the bit weights of the disconnected coordinates.
    """
    n = len(dyn)
    params = params or {}
    C = [j for j, v in enumerate(cm[node0]) if v == 1]
    D = [j for j in range(n) if j not in C]
    L = []
    for assign in itertools.product([0, 1], repeat=len(C)):
        state = [0] * n
        for j, b in zip(C, assign):
            state[j] = b
        if ca._eval_gate(dyn[node0], [state[j] for j in C],
                         params.get(node0 + 1, {})) == value:
            L.append(sum(state[j] << j for j in range(n)))
    Omega = sorted({sum(w) for r in range(len(D) + 1)
                    for w in itertools.combinations([1 << j for j in D], r)})
    return sorted(C), sorted(D), sorted(L), Omega


def deconvolve(L, Omega):
    return sorted({l + o for l in L for o in Omega})


def run_lengths(seq):
    """Flat run-length encoding: [(count, value), ...]."""
    out = []
    for v in seq:
        if out and out[-1][1] == v:
            out[-1][0] += 1
        else:
            out.append([1, v])
    return [(c, v) for c, v in out]


def sumset(*factors):
    """Direct sum of sets: {a + b + ... : a in A, b in B, ...}."""
    acc = {0}
    for f in factors:
        acc = {a + b for a in acc for b in f}
    return sorted(acc)


def factorise_offsets(D):
    """
    The offset family factorises into one independent binary choice per
    disconnected coordinate:

        Omega = {0, w_1} (+) {0, w_2} (+) ... (+) {0, w_k},   w_j = 2^(j-1)

    This is the generative structure, and it is exact rather than pattern-matched.
    The recursion is what a flat run-length listing destroys: the same activation
    pattern recurs at every partial sum of the free weights, which is precisely why
    the sequence looks self-similar at dyadic scales.
    """
    return [[0, 1 << j] for j in D]


def fmt_factors(factors):
    return " (+) ".join("{" + ",".join(map(str, f)) + "}" for f in factors)


def main() -> None:
    n = len(DYN07)
    node0 = NODE - 1

    col = isolated_output(CM07, DYN07, node0)
    C, D, L, Omega = base_and_offsets(CM07, DYN07, node0)
    reconstructed = deconvolve(L, Omega)
    exhaustive = [i for i, v in enumerate(col) if v == 1]

    flat = run_lengths(col)
    factors = factorise_offsets(D)

    print("=" * 68)
    print(f"  Worked example — node {NODE} of the 7-node network")
    print("=" * 68)
    print(f"  gate                    : {DYN07[node0]}")
    print(f"  connected inputs C      : {[j+1 for j in C]}   weights {[1 << j for j in C]}")
    print(f"  disconnected      D     : {[j+1 for j in D]}   weights {[1 << j for j in D]}")
    print(f"  repertoire length       : {len(col)} = 2^{n}")
    print()
    print(f"  base set     L          : {L}")
    print(f"      (sum of connected weights = {sum(1 << j for j in C)})")
    print(f"  offset family Omega     : {Omega}")
    print(f"      (all subset sums of {[1 << j for j in D]}; |Omega| = 2^{len(D)} = {len(Omega)})")
    print()
    print(f"  Dec(L, Omega)           : {reconstructed}")
    print(f"  exhaustive evaluation   : {exhaustive}")
    print(f"  identical               : {reconstructed == exhaustive}")
    print()
    flat_tokens = 2 * len(flat)
    rule_tokens = len(L) + len(D)

    print("  flat run-length encoding (a tally — this is NOT the method):")
    print("    " + ", ".join(f"{c}->{v}" for c, v in flat))
    print(f"    {len(flat)} runs, {flat_tokens} tokens; it records the sequence but")
    print("    generates nothing, and it is blind to why the gaps have these lengths.")
    print()
    print("  generative rule — the offset family factorises:")
    print(f"    Omega = {fmt_factors(factors)}")
    print(f"    one-set = L (+) Omega,  L = {L}")
    print(f"    {rule_tokens} tokens: one pivot and {len(D)} free weights.")
    print("    Each free coordinate contributes an independent binary choice, so the")
    print("    activation pattern recurs at every partial sum of the free weights.")
    print("    That recursion is the self-similarity; the flat form destroys it.")
    print()

    checks = [
        ("Dec(L, Omega) reproduces the exhaustive one-set", reconstructed == exhaustive),
        ("|Omega| = 2^(n - |C|)", len(Omega) == 2 ** (n - len(C))),
        ("|one-set| = |L| * |Omega|", len(reconstructed) == len(L) * len(Omega)),
        ("L = {sum of connected weights} for AND", L == [sum(1 << j for j in C)]),
        ("Omega equals the sumset of its free-weight factors", sumset(*factors) == Omega),
        ("generative rule is shorter than the flat tally", rule_tokens < flat_tokens),
    ]
    for name, ok in checks:
        print(f"    {'PASS' if ok else 'FAIL'}  {name}")
    all_ok = all(ok for _, ok in checks)
    print(f"\n  Overall: {'PASS' if all_ok else 'FAIL'}")
    print("=" * 68)

    here = Path(__file__).parent
    (here / "worked_example_7node.json").write_text(json.dumps({
        "network": {"cm": CM07, "dyn": DYN07},
        "node": NODE,
        "gate": DYN07[node0],
        "connected_inputs_1based": [j + 1 for j in C],
        "disconnected_1based": [j + 1 for j in D],
        "base_set_L_0based": L,
        "offset_family_Omega": Omega,
        "one_set_0based": reconstructed,
        "one_set_1based": [i + 1 for i in reconstructed],
        "flat_run_lengths": flat,
        "offset_factorisation": fmt_factors(factors),
        "flat_tokens": flat_tokens,
        "rule_tokens": rule_tokens,
        "isolated_output": "".join(map(str, col)),
        "checks_pass": all_ok,
    }, indent=2), encoding="utf-8")

    # LaTeX fragment, 1-based to match the manuscript's index universe.
    tex = [
        r"% Auto-generated by papers/method/code/worked_example_7node/worked_example_7node.py",
        r"\newcommand{\wexGate}{" + DYN07[node0] + r"}",
        r"\newcommand{\wexInputs}{\{" + ",".join(str(j + 1) for j in C) + r"\}}",
        r"\newcommand{\wexFree}{\{" + ",".join(str(j + 1) for j in D) + r"\}}",
        r"\newcommand{\wexBase}{\{" + ",".join(str(l + 1) for l in L) + r"\}}",
        r"\newcommand{\wexOffsets}{\{" + ",".join(map(str, Omega)) + r"\}}",
        r"\newcommand{\wexOneSet}{\{" + ",".join(str(i + 1) for i in reconstructed) + r"\}}",
    ]
    (here / "worked_example_7node.tex").write_text("\n".join(tex) + "\n", encoding="utf-8")
    print("\n  Written: worked_example_7node.json, worked_example_7node.tex")


if __name__ == "__main__":
    main()
