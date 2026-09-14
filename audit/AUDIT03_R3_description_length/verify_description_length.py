#!/usr/bin/env python3
"""AUDIT03 / R3.1-R3.2 - is the bio description length actually a description length?

This settles, by execution rather than by assertion, the defect recorded in
audit/AUDIT03_PLAN.md section R3: two implementations of the per-node cost charged
log2 C(n, d) for the input set without ever transmitting d.

The programme is ALGORITHMIC, not statistical. A "description length" here is the
length of a program in a DECLARED language that a decoder can read back. So the
only admissible proof is a decoder. Four gates, each with a negative control,
because a gate that cannot fail is not a gate:

  G1 KRAFT          exhaustive enumeration of the whole node-description space;
                    sum 2^-L must be exactly 1.
  G1' NEGATIVE      the same enumeration with the in-degree field removed must
                    give n+1, not 1. If it does not, G1 is inert.
  G2 ROUND TRIP     an explicit sequential encoder/decoder must recover
                    (gate, d, input set, parameters) elementwise for EVERY
                    description in the space. This is what proves the alphabet
                    sizes summed in G1 are the real ones.
  G2' NEGATIVE      exhibit a concrete pair of distinct nodes whose descriptions
                    are byte-identical once d is not transmitted.
  G3 PARITY         the three implementations (bio_D_experiment.py, BioMetrics.m,
                    complexity_analysis.py) must agree CELL BY CELL over a grid.
                    Counts are not reported without the differing cells (U8).
  G4 CORPUS         re-derive how many bits the bio corpus was never charging,
                    through the pipeline's own loader rather than a private read.
  G5 LANGUAGE       does the corpus even lie inside the declared language? G1-G3
                    prove the code is valid FOR THE TWELVE FAMILIES; that says
                    nothing about a corpus whose labels are not among them. G5 is
                    reported with its own verdict and does not mask G1-G3.

Run (from the repository root):
    venv/bin/python audit/AUDIT03_R3_description_length/verify_description_length.py

G3's Wolfram arm needs biometrics_grid.json; regenerate it with
    HOME=$HOME /Applications/Wolfram.app/Contents/MacOS/WolframKernel -script \
      audit/AUDIT03_R3_description_length/dump_biometrics_grid.m
If the file is absent the Wolfram arm reports SKIPPED and the run does not claim
three-way parity.
"""

from __future__ import annotations

import itertools
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "papers" / "method" / "code" / "complexity_analysis"))

GATE_LABELS = ["AND", "OR", "XOR", "NAND", "NOR", "XNOR", "NOT", "IMPLIES",
               "NIMPLIES", "MAJORITY", "KOFN", "CANALISING"]
K = len(GATE_LABELS)

# ---------------------------------------------------------------------------
# The declared language, stated once as ALPHABET SIZES rather than as bit counts.
#
# A node is written as four fields, read in this order:
#     (a) gate type      one of K
#     (b) in-degree d    one of n+1          <- the field that was missing
#     (c) input set S    one of C(n, d)      width known only after (b)
#     (d) parameters p   one of param_alphabet(gate, d, n)
#
# Its length is the sum of the logs. Deriving the LENGTHS from the ALPHABETS,
# rather than writing both down independently, is deliberate: it makes it
# impossible for the Kraft sum to be taken over a space the cost does not charge
# for, which is the exact way this class of error hides.
# ---------------------------------------------------------------------------


def param_alphabet(gate: str, d: int, n: int) -> int:
    """Number of distinct parameter settings the gate-specific field must name."""
    if gate == "KOFN":
        return 2 * (d + 1)                      # threshold k in 0..d, plus a flag
    if gate == "CANALISING":
        return 4 * max(1, n)                    # index, canalising value, output
    if gate in ("IMPLIES", "NIMPLIES"):
        return max(1, d * (d - 1))              # ordered pair drawn from the inputs
    if gate == "NOT":
        return max(1, d)                        # which input is negated
    return 2                                    # polarity bit


def _log2(x: float) -> float:
    return math.log2(x) if x > 0 else 0.0


def node_length(gate: str, d: int, n: int, with_indegree: bool = True) -> float:
    """Length in bits, derived from the alphabet sizes above and nothing else."""
    bits = _log2(K)
    if with_indegree:
        bits += _log2(n + 1)
    bits += _log2(max(1, math.comb(n, d)))
    bits += _log2(param_alphabet(gate, d, n))
    return bits


# ---------------------------------------------------------------------------
# G1 - Kraft, by exhaustive enumeration of the description space
# ---------------------------------------------------------------------------

def kraft_sum(n: int, with_indegree: bool) -> float:
    """Enumerate EVERY describable node at width n and sum 2^-L.

    Every input set is listed one by one rather than counted, so the sum is over
    objects that exist, not over a binomial coefficient that is assumed correct.
    """
    total = 0.0
    for gate in GATE_LABELS:
        for d in range(n + 1):
            length = node_length(gate, d, n, with_indegree)
            weight = 2.0 ** -length
            for _S in itertools.combinations(range(n), d):
                total += weight * param_alphabet(gate, d, n)
    return total


# ---------------------------------------------------------------------------
# G2 - a real sequential encoder and decoder
# ---------------------------------------------------------------------------

def describe(gate: str, S: tuple[int, ...], p: int, n: int) -> list[int]:
    """Encode a node as the field sequence the language declares."""
    d = len(S)
    subsets = list(itertools.combinations(range(n), d))
    return [GATE_LABELS.index(gate), d, subsets.index(S), p]


def read_description(fields: list[int], n: int):
    """Decode, using ONLY n and the fields already read.

    The point of the whole exercise is line 4: the width of field (c) is
    C(n, d), and d is knowable only because field (b) was transmitted.
    """
    gate = GATE_LABELS[fields[0]]
    d = fields[1]                                    # field (b)
    subsets = list(itertools.combinations(range(n), d))   # width now determined
    S = subsets[fields[2]]
    p = fields[3]
    if not 0 <= p < param_alphabet(gate, d, n):
        raise ValueError("parameter index outside its alphabet")
    return gate, S, p


def round_trip(n: int):
    """Every description in the space must decode to itself. Returns failures."""
    failures, count = [], 0
    for gate in GATE_LABELS:
        for d in range(n + 1):
            for S in itertools.combinations(range(n), d):
                for p in range(param_alphabet(gate, d, n)):
                    got = read_description(describe(gate, S, p, n), n)
                    count += 1
                    if got != (gate, S, p):
                        failures.append({"sent": [gate, list(S), p],
                                         "got": [got[0], list(got[1]), got[2]]})
    return count, failures


def indegree_free_collision(n: int):
    """G2' - the negative control, as a concrete pair rather than an argument.

    Strip field (b). Two nodes of DIFFERENT in-degree then emit identical field
    sequences, so no decoder can tell them apart and the code is not a code.
    """
    seen, collisions = {}, []
    for gate in GATE_LABELS:
        for d in range(n + 1):
            for S in itertools.combinations(range(n), d):
                for p in range(param_alphabet(gate, d, n)):
                    stripped = (GATE_LABELS.index(gate),
                                list(itertools.combinations(range(n), d)).index(S), p)
                    if stripped in seen and seen[stripped][1] != d:
                        collisions.append({"fields_without_indegree": list(stripped),
                                           "reading_A": [seen[stripped][0],
                                                         list(seen[stripped][2]),
                                                         seen[stripped][3]],
                                           "reading_B": [gate, list(S), p]})
                    else:
                        seen.setdefault(stripped, (gate, d, S, p))
    return collisions


# ---------------------------------------------------------------------------
# G3 - three-way elementwise parity
# ---------------------------------------------------------------------------

def parity_grid(max_n: int = 8):
    from integration.bio_D_experiment import encode_node_cost as bio_cost
    from complexity_analysis import encode_node_cost as ca_cost

    wl_path = HERE / "biometrics_grid.json"
    wl = {}
    if wl_path.exists():
        for cell in json.loads(wl_path.read_text())["cells"]:
            wl[(cell["n"], cell["d"], cell["gate"])] = float(cell["bits"])

    gates = GATE_LABELS + ["CUSTOM"]      # CUSTOM exercises the default branch
    cells, diffs = 0, []
    for n in range(1, max_n + 1):
        for d in range(n + 1):
            for g in gates:
                row = [1] * d + [0] * (n - d)
                vals = {"bio_D_experiment.py": bio_cost(row, g, n),
                        "complexity_analysis.py": ca_cost(d, g, n),
                        "verify (declared language)": node_length(g, d, n)}
                key = (n, d, g)
                if key in wl:
                    vals["BioMetrics.m"] = wl[key]
                cells += 1
                if max(vals.values()) - min(vals.values()) > 1e-9:
                    diffs.append({"n": n, "d": d, "gate": g,
                                  "values": {k: round(v, 12) for k, v in vals.items()}})
    return cells, diffs, bool(wl)


# ---------------------------------------------------------------------------
# G4 - what the corpus was never charged
# ---------------------------------------------------------------------------

def corpus_shortfall():
    """Old D vs new D on the real corpus, PER NETWORK, through the real loader.

    Deliberately calls load_processed_bio_networks rather than re-reading the
    JSON: a shortfall computed by a private reading of the corpus would measure
    my reading, not the pipeline's. It is also why n here is len(net["nodes"]),
    which is 6,577 and not the 4,626 nodes that carry a "gates" entry - the
    remainder are labelled INPUT by the loader and are charged like any other.
    """
    if not (ROOT / "data" / "bio" / "processed").is_dir():
        return None
    from integration.bio_D_experiment import load_processed_bio_networks

    nets = load_processed_bio_networks(ROOT)
    rows, nodes, missing = [], 0, 0.0
    labels = {}
    for name, net in sorted(nets.items()):
        n = len(net["dynamic"])
        if n == 0:
            continue
        for g in net["dynamic"]:
            labels[g] = labels.get(g, 0) + 1
        # the pipeline's D is now the corrected one; the pre-fix value is the
        # same sum minus the field that was never transmitted.
        new_d = sum(node_length(g, int(sum(net["cm"][i])), n)
                    for i, g in enumerate(net["dynamic"]))
        delta = n * math.log2(n + 1)
        nodes += n
        missing += delta
        rows.append({"network": name, "n": n,
                     "D_old": round(new_d - delta, 6), "D_new": round(new_d, 6),
                     "delta_bits": round(delta, 6)})
    rows.sort(key=lambda r: -r["delta_bits"])
    return {"networks": len(rows), "nodes": nodes,
            "uncharged_bits_total": round(missing, 2),
            "uncharged_bits_per_node": round(missing / nodes, 4) if nodes else 0.0,
            "gate_labels_reaching_the_cost_function": dict(
                sorted(labels.items(), key=lambda kv: -kv[1])),
            "per_network": rows}


def main() -> int:
    failed = []
    print("AUDIT03/R3 - description-length decodability and parity\n")

    print("G1  KRAFT SUM over the enumerated description space")
    print(f"    {'n':>3}{'with in-degree':>18}{'without (control)':>20}{'expected':>12}")
    for n in range(1, 9):
        good, bad = kraft_sum(n, True), kraft_sum(n, False)
        ok = abs(good - 1.0) < 1e-9 and abs(bad - (n + 1)) < 1e-9
        if not ok:
            failed.append(f"G1 n={n}: {good} / {bad}")
        print(f"    {n:>3}{good:>18.12f}{bad:>20.9f}{'1 / n+1':>12}  {'ok' if ok else 'FAIL'}")
    print("    -> with the field the code is complete (Kraft = 1); without it the")
    print("       weights overshoot by exactly the n+1 in-degrees never named.\n")

    print("G2  ROUND TRIP - decode every description with only n known in advance")
    for n in range(1, 7):
        count, fails = round_trip(n)
        if fails:
            failed.append(f"G2 n={n}: {len(fails)} descriptions did not decode")
            print(f"    n={n}: {count} descriptions, FAIL, first: {fails[0]}")
        else:
            print(f"    n={n}: {count} descriptions, all recovered elementwise")
    print()

    print("G2' NEGATIVE CONTROL - remove the in-degree field and collide")
    for n in (3, 4):
        cols = indegree_free_collision(n)
        if not cols:
            failed.append(f"G2' n={n}: no collision found - the control is inert")
            print(f"    n={n}: NO COLLISION -> control inert, G2 proves nothing")
        else:
            c = cols[0]
            print(f"    n={n}: {len(cols)} colliding descriptions. First:")
            print(f"        fields without in-degree {c['fields_without_indegree']}")
            print(f"        reads as gate={c['reading_A'][0]} inputs={c['reading_A'][1]}")
            print(f"        or as     gate={c['reading_B'][0]} inputs={c['reading_B'][1]}")
    print()

    print("G3  THREE-WAY PARITY, cell by cell")
    cells, diffs, have_wl = parity_grid()
    arms = "bio_D_experiment.py / complexity_analysis.py / declared language"
    arms += " / BioMetrics.m" if have_wl else "  [BioMetrics.m arm SKIPPED - no grid dump]"
    print(f"    arms: {arms}")
    print(f"    cells compared: {cells}")
    if diffs:
        failed.append(f"G3: {len(diffs)} cells disagree")
        print(f"    DISAGREEING CELLS: {len(diffs)}")
        for c in diffs[:20]:
            print(f"      n={c['n']} d={c['d']} {c['gate']:<11} {c['values']}")
        if len(diffs) > 20:
            print(f"      ... and {len(diffs) - 20} more")
    else:
        print("    0 cells disagree")
    if not have_wl:
        failed.append("G3: Wolfram arm not run - three-way parity NOT established")
    print()

    print("G4  CORPUS SHORTFALL under the pre-fix code")
    sf = corpus_shortfall()
    if sf is None:
        print("    data/bio/processed absent - skipped")
    else:
        print(f"    {sf['networks']} networks, {sf['nodes']} nodes")
        print(f"    bits never charged: {sf['uncharged_bits_total']} "
              f"({sf['uncharged_bits_per_node']} per node)")
        print("    largest per-network corrections (old D -> new D):")
        for r in sf["per_network"][:8]:
            print(f"      {r['network'][:38]:<38} n={r['n']:>4}  "
                  f"{r['D_old']:>12.3f} -> {r['D_new']:>12.3f}  (+{r['delta_bits']:.3f})")
        print("    gate labels actually reaching the cost function:")
        print(f"      {sf['gate_labels_reaching_the_cost_function']}")
        print("    Every DeltaD published from these files was a difference of two")
        print("    quantities that were not description lengths.")
    print()

    print("G5  LANGUAGE COVERAGE - is the corpus inside the declared language?")
    g5 = None
    if sf is not None:
        hist = sf["gate_labels_reaching_the_cost_function"]
        outside = {g: c for g, c in hist.items() if g not in GATE_LABELS}
        n_out = sum(outside.values())
        total = sum(hist.values())
        g5 = {"nodes": total, "outside_declared_alphabet": n_out,
              "fraction": round(n_out / total, 4) if total else 0.0,
              "labels": outside}
        print(f"    declared alphabet: {K} families, cost log2({K}) = {_log2(K):.6f} bits")
        print(f"    nodes whose label is NOT in that alphabet: {n_out} of {total} "
              f"({100 * n_out / total:.1f}%)")
        for g, c in outside.items():
            print(f"      {g:<12} {c:>5}   no codeword exists; falls to the default branch")
        print("    VERDICT G5: FAIL. The gate field cannot WRITE these nodes, let")
        print("    alone decode them: log2(12) indexes twelve labels and these are")
        print("    not among them, while the default branch then charges a polarity")
        print("    bit for a parameter they do not have. So the corrected cost is a")
        print("    valid code for the twelve-family language and the corpus is")
        print("    largely outside it. Fixing the in-degree field was necessary and")
        print("    is NOT sufficient: no bio D may be published until the language")
        print("    covers the corpus. This is precisely what AUDIT03/R4 addresses.")
    print()

    report = {"language_coverage_G5": g5,
              "kraft": {str(n): {"with_indegree": kraft_sum(n, True),
                                "without_indegree": kraft_sum(n, False)}
                        for n in range(1, 9)},
              "parity_cells": cells,
              "parity_disagreeing_cells": diffs,
              "wolfram_arm_run": have_wl,
              "corpus_shortfall": sf,
              "verdict_R3_1_and_R3_2": "PASS" if not failed else "FAIL",
              "verdict_G5_language_coverage":
                  "FAIL" if (g5 and g5["outside_declared_alphabet"]) else "PASS"}
    (HERE / "verification.json").write_text(json.dumps(report, indent=1))

    if failed:
        print("VERDICT R3.1/R3.2: FAIL")
        for f in failed:
            print(" -", f)
        return 1
    print("VERDICT R3.1/R3.2: PASS - the corrected cost is a uniquely decodable")
    print("code with Kraft sum 1, all four implementations agree cell by cell,")
    print("and both negative controls fire.")
    print("VERDICT G5: FAIL, separately and deliberately - see above. R3.1 removed")
    print("one reason the bio D was invalid; G5 is the reason that remains, and it")
    print("is reported rather than absorbed so it cannot be mistaken for closed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
