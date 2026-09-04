#!/usr/bin/env python3
"""AUDIT03/R1.3 — re-do the catalogue-expansion accounting in PROGRAM LENGTH.

CATALOGUE_EXPANSION.md priced the naming field with an EMPIRICAL GATE ENTROPY:

    empirical gate entropy H(p) = 2.070 bits/node
    uniform code over the same labels = 3.170 bits/node
    ... saving 18.36 bits/node, ~84,900 bits over the corpus

That is a Shannon quantity and this programme is algorithmic. It is also the
wrong quantity for the question. A frequency-weighted code is only shorter than
a uniform one if the DECODER ALREADY HAS THE FREQUENCY TABLE, and that table is
never transmitted -- it is estimated from the very corpus being priced. Charging
H(p) per node is charging for a model fitted to the data and then not paying for
the model. The uniform log2(K) index is the honest catalogue cost, because a
catalogue of K families genuinely costs log2(K) to index and nothing else.

So the accounting is redone with no entropy in it anywhere.

  cost of expanding 12 -> 13 : log2(13) - log2(12), paid by EVERY node,
                               because every node's gate field widens.
  saving                     : a node whose gate the new family names stops
                               paying a raw 2^d truth table and pays the
                               family's parameter field instead.

The parameter field is not a free choice. REGULATORY_DNF is a disjunction of
activator/inhibitor clauses, which is EXACTLY a set of schemata over the node's
connected inputs -- so its parameter field is the schema-normal-form field
already defined and owned by src/description_lengths.py. The thirteenth family
does not need a new cost model; it inherits D_schema's.

WHAT THIS CANNOT SETTLE. The saving is realised only for nodes the closed form
ACTUALLY reproduces, and that fraction is R4.1's measurement and is not yet
made. Every saving below is therefore reported as an UPPER BOUND with the
coverage fraction left as a free variable, and the break-even coverage is
reported alongside it -- that is the number which does not depend on R4.1.

Run:
    venv/bin/python audit/AUDIT03_R1_correct_the_record/catalogue_expansion_program_length.py
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import description_lengths as dl  # noqa: E402

LINE = "-" * 78
CANONICAL = {"AND", "OR", "XOR", "NAND", "NOR", "XNOR", "NOT",
             "IMPLIES", "NIMPLIES", "MAJORITY", "KOFN", "CANALISING"}
# The operator vocabulary CATALOGUE_EXPANSION.md decomposed the CUSTOM formulas
# into. A formula built only from these three is in REGULATORY_DNF's reach.
BOOLEAN_ONLY = re.compile(r"^[\sA-Za-z0-9_:.\-()!&|]*$")
NON_BOOLEAN = re.compile(r"<=|>=|==|<|>|\bGEQ\b|\bLEQ\b|\bLT\b|\bGT\b|\bEQ\b")


def part(t: str) -> None:
    print(f"\n{LINE}\n{t}\n{LINE}")


def load_nodes():
    """Every node of the processed corpus with its gate label, in-degree and
    formula, so the accounting is measured rather than transcribed."""
    out = []
    for path in sorted((ROOT / "data" / "bio" / "processed").glob("*.json")):
        net = json.loads(path.read_text())
        if "cm" not in net or "gates" not in net or "nodes" not in net:
            continue
        nodes, cm, gates = net["nodes"], net["cm"], net.get("gates", {})
        logic = net.get("logic", {}) or {}
        n = len(nodes)
        for i, node in enumerate(nodes):
            gi = gates.get(node)
            d = sum(cm[i]) if i < len(cm) else 0
            out.append({
                "network": net.get("name", path.stem), "n": n, "d": d,
                "gate": (gi or {}).get("gate", "INPUT"),
                "formula": logic.get(node, "") or "",
            })
    return out


def main() -> int:
    print("AUDIT03/R1.3 — catalogue expansion priced as PROGRAM LENGTH")
    nodes = load_nodes()

    part("G1 — RENDER THE CORPUS BEFORE PRICING IT")
    custom = [x for x in nodes if x["gate"] not in CANONICAL]
    named = [x for x in nodes if x["gate"] in CANONICAL]
    print(f"  nodes total                 : {len(nodes)}")
    print(f"  named by a canonical family : {len(named)}")
    print(f"  not named (fall through)    : {len(custom)}"
          f"  ({100*len(custom)/len(nodes):.1f}%)")
    reach = [x for x in custom if x["formula"]
             and not NON_BOOLEAN.search(x["formula"])]
    thresh = [x for x in custom if x["formula"]
              and NON_BOOLEAN.search(x["formula"])]
    noform = [x for x in custom if not x["formula"]]
    print(f"    of those, Boolean-only formulas : {len(reach)}")
    print(f"    threshold / multi-valued        : {len(thresh)}"
          f"   (NOT a Boolean gate; out of scope)")
    print(f"    no formula recorded             : {len(noform)}")

    dd = [x["d"] for x in reach]
    if dd:
        print(f"  in-degree of the reachable set: min {min(dd)}, "
              f"median {sorted(dd)[len(dd)//2]}, max {max(dd)}")

    part("R1.3a — THE COST, paid by every node")
    per_node = math.log2(13) - math.log2(12)
    print(f"  log2(13) - log2(12) = {per_node:.4f} bits/node")
    print(f"  over {len(nodes)} nodes: {per_node*len(nodes):.1f} bits")
    print("  This is the whole cost. It is charged to EVERY node, including the")
    print("  ones that gain nothing, because the gate field widens for all.")

    part("R1.3b — THE SAVING, converted from an unknown into a THRESHOLD")
    print("  BOTH forms are priced FULL, in a common coordinate. A fall-through")
    print("  node pays log2(n+1) for its in-degree, log2 C(n,d) to name which")
    print("  inputs, and 2^d for the raw table. Comparing 2^d alone against the")
    print("  schema form's full cost would under-charge the table by the two")
    print("  fields it also needs; the first version of this script did exactly")
    print("  that and made expansion look far worse than it is.")
    print("  Under family 13 the node pays the schema field,")
    print("  which is REGULATORY_DNF's parameter field by construction:")
    print("      gamma(s+1) + s * [ log2(n+1) + log2 C(n,k) + k ]")
    print("  for s clauses fixing k coordinates each.")
    print()
    print("  s is NOT KNOWN without the truth tables, and obtaining them is")
    print("  R4.1. Inventing a worst case would be assuming the answer, so the")
    print("  unknown is converted into a threshold instead: s_max is the largest")
    print("  clause count at which the schema field is still cheaper than the")
    print("  raw table. Above s_max, expansion LOSES on that node.")
    print("  k = d is used per clause, the most expensive clause possible.")
    print()
    print(f"  {'d':>3}{'nodes':>7}{'median n':>10}{'LUT full':>10}"
          f"{'1 clause':>10}{'s_max':>8}{'verdict':>22}")
    by_d: dict[int, dict] = {}
    tot_lut = 0.0
    for d in sorted({x["d"] for x in reach}):
        grp = [x for x in reach if x["d"] == d]
        ns = sorted(x["n"] for x in grp)
        n = max(1, ns[len(ns) // 2])
        k = min(d, n)
        # FULL cost of the raw-table form: the decoder needs the in-degree and
        # the input set before the table means anything.
        lut = (math.log2(n + 1) + math.log2(max(1, math.comb(n, d)))
               + float(2 ** d))
        per_clause = math.log2(n + 1) + math.log2(max(1, math.comb(n, k))) + k
        s_max = 0
        while True:
            s = s_max + 1
            if dl._gamma_len(s + 1) + s * per_clause <= lut:
                s_max = s
                if s_max > 4096:
                    break
            else:
                break
        one = dl._gamma_len(2) + per_clause
        verdict = ("never cheaper" if s_max == 0
                   else f"cheaper if s <= {s_max}")
        tot_lut += lut * len(grp)
        by_d[d] = {"nodes": len(grp), "median_n": n, "lut_bits": lut,
                   "one_clause_bits": one, "s_max": s_max}
        print(f"  {d:>3}{len(grp):>7}{n:>10}{lut:>10.1f}{one:>10.1f}"
              f"{s_max:>8}{verdict:>22}")

    losers = [d for d, v in by_d.items() if v["s_max"] == 0]
    n_losers = sum(by_d[d]["nodes"] for d in losers)
    print(f"\n  On in-degrees {losers} the schema field is NEVER cheaper than the")
    print(f"  raw table -- {n_losers} of {len(reach)} reachable nodes"
          f" ({100*n_losers/len(reach):.1f}%). At small d a raw table is only a")
    print("  handful of bits and naming the coordinates costs more than listing")
    print("  the answers. Expansion cannot pay for those nodes, ever, and the")
    print("  superseded figure charged a saving on every one of them.")
    gross = 0.0

    part("R1.3c — WHAT IS NOT KNOWN, and the number that does not depend on it")
    print("  The saving is realised only on nodes the closed form actually")
    print("  reproduces. That fraction is R4.1's measurement and is NOT MADE.")
    print("  So the figure above is an upper bound at coverage = 1, and the")
    print("  honest report is the break-even coverage:")
    print(f"  Cost is fixed and known: {per_node*len(nodes):,.1f} bits over the corpus.")
    print("  Saving is bounded above by the per-d thresholds and is ZERO wherever")
    print("  s_max = 0. No net figure is quoted, because quoting one would require")
    print("  the clause counts, and those are R4.1.")
    print("\n  The superseded figure was 18.36 bits/node / ~84,900 bits over the")
    print("  corpus. It must not be quoted: its naming term was an entropy, and")
    print("  its saving assumed coverage = 1 without saying so.")

    out = {
        "nodes_total": len(nodes), "custom": len(custom),
        "reachable_boolean_only": len(reach),
        "threshold_multivalued": len(thresh), "no_formula": len(noform),
        "cost_per_node_bits": per_node,
        "cost_total_bits": per_node * len(nodes),
        "clause_count_thresholds_by_in_degree": by_d,
        "in_degrees_where_expansion_can_never_pay": losers,
        "nodes_where_expansion_can_never_pay": n_losers,
        "by_in_degree": by_d,
        "supersedes": {"figure": "18.36 bits/node, ~84,900 bits",
                       "reason": "naming term was Shannon entropy H(p)=2.070; "
                                 "saving assumed coverage=1 implicitly"},
    }
    (HERE / "catalogue_expansion_program_length.json").write_text(
        json.dumps(out, indent=1, default=str))
    print(f"\nwritten: {HERE / 'catalogue_expansion_program_length.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
