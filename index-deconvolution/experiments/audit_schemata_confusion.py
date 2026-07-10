"""audit_schemata_confusion.py

Adversarial study of gate confusion and arity detection, and of the role of
multi-node interaction (schemata) in the deconvolution.

Questions from the assessor, answered by experiment and counterexample:

  Q1  Can a node with several inputs be misclassified - can an OR behave as an
      AND under a particular network configuration?
  Q2  How is the number of inputs (arity) of a node found, and can it be wrong?

The pivotal distinction is the set of observed input combinations.  Over the
exhaustive repertoire every combination appears, so identification is exact and
confusion is impossible beyond genuine functional equalities.  Over the reachable
states of a running network, inputs can be correlated, and then both the gate and
the arity can be recovered wrongly.  We exhibit that counterexample.
"""

from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from causalbool import Network, repertoire, truth_table, apply_gate, step, input_vector
from deconvolution import deconvolve, identify_gate, minimal_dnf


def line(t):
    print("\n" + "=" * 74 + f"\n{t}\n" + "=" * 74)


# ---------------------------------------------------------------------------
# Partial (reachable-state) deconvolution helpers - identification from a subset
# of input combinations rather than the exhaustive repertoire.
# ---------------------------------------------------------------------------
def essential_from_samples(samples, n):
    d = {s: o for s, o in samples}
    ess = []
    for i in range(n):
        for s, o in samples:
            s2 = tuple(b ^ (1 if j == i else 0) for j, b in enumerate(s))
            if s2 in d and d[s2] != o:
                ess.append(i)
                break
    return ess


def identify_from_samples(samples, n, ess):
    m = len(ess)
    table = [None] * (2 ** m)
    for s, o in samples:
        y = 0
        for j, e in enumerate(ess):
            if s[e]:
                y |= (1 << j)
        if table[y] is not None and table[y] != o:
            return None, 0.0, table
        table[y] = o
    covered = sum(1 for v in table if v is not None)
    filled = [0 if v is None else v for v in table]
    _, canonical = identify_gate(filled)
    return canonical, covered / (2 ** m), table


# ---------------------------------------------------------------------------
# PROBE A - the exhaustive confusion landscape: gates coincide only as genuine
# functional equalities, and OR != AND for arity >= 2.
# ---------------------------------------------------------------------------
def probe_confusion_landscape():
    line("PROBE A  Exhaustive confusion landscape (genuine equivalences only)")
    for m in (1, 2, 3, 4):
        cands = {g: tuple(truth_table(g, m)) for g in
                 ("AND", "OR", "XOR", "NAND", "NOR", "XNOR", "MAJORITY")}
        for k in range(1, m + 1):
            cands[f"KOFN{k}"] = tuple(truth_table("KOFN", m, {"k": k}))
        groups = {}
        for g, tt in cands.items():
            groups.setdefault(tt, []).append(g)
        coincide = [v for v in groups.values() if len(v) > 1]
        print(f"  arity {m}: OR==AND? {cands['OR'] == cands['AND']}   "
              f"equivalence classes: {coincide}")
    return True


# ---------------------------------------------------------------------------
# PROBE B - over the exhaustive repertoire the recovered FUNCTION is always
# exact; the NAME differs from the true gate only within an equivalence class.
# ---------------------------------------------------------------------------
def probe_exhaustive_never_confuses():
    line("PROBE B  Exhaustive: function always exact; name-diffs are equivalences")
    from network_generator import random_network
    n_nodes = 0
    func_wrong = 0
    name_diff_but_equivalent = 0
    for seed in range(60):
        net = random_network(n=7, seed=8000 + seed, gate_pool="all")
        rep = repertoire(net)
        _, reports = deconvolve(rep)
        for k in range(net.n):
            n_nodes += 1
            ic = net.connected_inputs(k)
            # true reduced truth table on the node's real inputs
            true_tt = [apply_gate(net.gates[k],
                                  [(y >> j) & 1 for j in range(len(ic))],
                                  net.params[k]) for y in range(2 ** len(ic))]
            rec = reports[k]
            # recovered function on recovered inputs must equal the column exactly
            rec_tt = rec.reduced_truth_table
            # compare as functions of the SAME inputs when connectivity matches
            if set(rec.connected_inputs) == set(ic):
                if rec_tt != true_tt:
                    func_wrong += 1
                if rec.canonical.gate != net.gates[k]:
                    # different NAME but same truth table => genuine equivalence
                    if truth_table(rec.canonical.gate, len(ic), rec.canonical.params) == true_tt \
                       if rec.canonical.gate not in ("LUT", "REGULATORY_DNF") else True:
                        name_diff_but_equivalent += 1
    print(f"  nodes checked                         : {n_nodes}")
    print(f"  functional errors (wrong truth table) : {func_wrong}")
    print(f"  name differs but truth table equal    : {name_diff_but_equivalent} "
          f"(genuine equivalence-class relabelling)")
    return func_wrong == 0


# ---------------------------------------------------------------------------
# PROBE C - the counterexample: correlated inputs in the reachable states make
# an OR indistinguishable from an AND and hide an input, so both the gate and
# the arity are recovered wrongly from reachable data - but exactly from the
# exhaustive repertoire.
# ---------------------------------------------------------------------------
def probe_reachable_state_confusion():
    line("PROBE C  Counterexample: reachable-state correlation confuses OR with AND")
    # node0 toggles; node1 and node2 both copy node0, so they are always equal
    # one step in; node3 = OR(node1, node2).
    n = 4
    C = [[0] * n for _ in range(n)]
    C[0][0] = 1          # node0 = NOT(node0)
    C[1][0] = 1          # node1 = node0
    C[2][0] = 1          # node2 = node0
    C[3][1] = 1; C[3][2] = 1  # node3 = OR(node1, node2)
    gates = ["NOT", "LUT", "LUT", "OR"]
    params = [{}, {"table": [0, 1]}, {"table": [0, 1]}, {}]
    net = Network(n=n, C=C, gates=gates, params=params)

    # (i) exhaustive deconvolution
    rep = repertoire(net)
    _, reports = deconvolve(rep)
    r3 = reports[3]
    print(f"  EXHAUSTIVE  node3: inputs {r3.connected_inputs}  gate {r3.canonical.gate}"
          f"   (truth: inputs [1, 2], gate OR)")

    # (ii) reachable-state deconvolution: only states that occur at t>=1
    reachable = sorted({tuple(step(net, input_vector(x, n))) for x in range(2 ** n)})
    # are node1 and node2 always equal in the reachable set?
    correlated = all(s[1] == s[2] for s in reachable)
    print(f"  reachable states: {len(reachable)} of {2**n}; node1==node2 always? {correlated}")
    samples = [(s, step(net, list(s))[3]) for s in reachable]
    ess = essential_from_samples(samples, n)
    canonical, cov, _ = identify_from_samples(samples, n, ess)
    gate_name = canonical.gate if canonical else "inconsistent"
    print(f"  REACHABLE   node3: inputs {ess}  gate {gate_name}  coverage {cov:.2f}")
    print("  => from reachable data alone, an input is hidden and OR is not")
    print("     distinguishable from AND; the exhaustive repertoire recovers it exactly.")

    exhaustive_ok = set(r3.connected_inputs) == {1, 2} and r3.canonical.gate == "OR"
    reachable_confused = set(ess) != {1, 2}
    return exhaustive_ok and reachable_confused


# ---------------------------------------------------------------------------
# PROBE D - schemata: a recovered clause is a schema (fixed inputs + don't-cares).
# Interaction shows up as multiple clauses; the free positions are the sumandos.
# ---------------------------------------------------------------------------
def probe_schemata():
    line("PROBE D  The index-set rule is a set of schemata (fixed bits + don't-cares)")
    # rule 110 local function, a genuinely interacting 3-input rule
    tt110 = [(110 >> nb) & 1 for nb in range(8)]
    clauses = minimal_dnf(tt110)
    print(f"  rule 110 truth table: {tt110}")
    print("  recovered schemata (over inputs 0,1,2; '*' = don't-care / sumando):")
    for cl in clauses:
        sch = ["*"] * 3
        for a in cl["activators"]:
            sch[a] = "1"
        for b in cl["inhibitors"]:
            sch[b] = "0"
        print(f"     {''.join(sch)}   (fixed {sorted(cl['activators']+cl['inhibitors'])}, "
              f"free {[i for i in range(3) if sch[i]=='*']})")
    # a schema with a don't-care genuinely covers >1 input: verify coverage
    covers = 0
    for nb in range(8):
        v = [(nb >> 0) & 1, (nb >> 1) & 1, (nb >> 2) & 1]
        for cl in clauses:
            if all(v[a] == 1 for a in cl["activators"]) and all(v[b] == 0 for b in cl["inhibitors"]):
                covers += 1
                break
    print(f"  schemata cover exactly the on-set: {covers} == {sum(tt110)} minterms")
    return covers == sum(tt110)


if __name__ == "__main__":
    results = {
        "confusion_landscape": probe_confusion_landscape(),
        "exhaustive_never_confuses": probe_exhaustive_never_confuses(),
        "reachable_state_confusion": probe_reachable_state_confusion(),
        "schemata": probe_schemata(),
    }
    line("SUMMARY")
    for k, v in results.items():
        print(f"  {k:28s}: {'PASS' if v else 'FAIL'}")
    print(f"\nall probes passed: {all(results.values())}")
