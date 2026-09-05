#!/usr/bin/env python3
"""AUDIT04 Phase 5 - why do 3,977 corpus nodes have "no derivable truth table"?

MEASUREMENT ONLY. This script does not repair the corpus, does not recompute a
description length and does not regenerate a bio number. The author gate on R4
stands; this exists so the decision behind that gate is made against a
decomposition rather than against a single aggregate.

THE CLAIM UNDER TEST, from audit/AUDIT03_PLAN.md R3.b:

    "76.4% of corpus nodes (3,977 of 5,204) carry a label outside the twelve,
     and their formulas are multi-valued threshold expressions already recorded
     unevaluable (AUDIT02/H). No description length of any kind reaches them."

The denominator reproduces exactly. The characterisation does not.

DENOMINATOR, and why three numbers are in circulation for one corpus:

    6,577  nodes in the `nodes` key across all 234 processed files
    5,204  nodes in the 170 files carrying `cm`, `gates` AND `nodes` together
    4,626  nodes that actually have an entry in the `gates` dict

5,204 is the one the record uses and the one used here. The gap to 4,626 is 578
nodes that are listed in `nodes` but absent from `gates`, which is itself part
of the finding rather than a rounding difference.

METHOD. A node is classified by attempting the thing that is claimed impossible:
building its truth table. Categories are decided by evaluation where evaluation
is possible, and by syntax only where it is not:

    no-gate-entry   listed in `nodes`, absent from `gates`
    source          in-degree 0; there is no update function to derive
    identity        y = x, in-degree 1, logic is the input's own name
    derivable       a full truth table was BUILT over 2^k assignments
    undeclared-vars the formula names variables absent from its `inputs` list
    multi-valued    the formula carries level references (`Pu1:2`, `ATM:1`)
    threshold       the formula carries GEQ/LEQ/GT/LT/EQ/NEQ against a free theta

Both Boolean spellings are accepted, because the corpus uses both:
`(PLCG | ICOS) & !LAG3` and `AND(OR(TH1e, TBET), NOT(GATA3))`. An earlier pass
of this analysis missed the second form and mis-scored 203 evaluable nodes as
unclassifiable; the two-spelling handling is the correction.

Usage:  venv/bin/python audit/AUDIT04_corpus_diagnostic/classify_corpus_nodes.py
"""
from __future__ import annotations

import collections
import glob
import itertools
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = str(ROOT / "data" / "bio" / "processed" / "*.json")

TWELVE = {"AND", "OR", "XOR", "NAND", "NOR", "XNOR", "NOT", "IMPLIES",
          "NIMPLIES", "MAJORITY", "KOFN", "CANALISING"}
THRESH = re.compile(r"\b(GEQ|LEQ|GT|LT|EQ|NEQ)\s*\(")
LEVEL = re.compile(r"\b[A-Za-z_][\w]*\s*:\s*\d+")
IDENT = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
MAX_ARITY = 16          # 2^16 rows; beyond this the table is not built

FUNCS = {
    "AND": lambda *a: all(a), "OR": lambda *a: any(a), "NOT": lambda x: not x,
    "XOR": lambda *a: sum(map(bool, a)) % 2 == 1,
    "NAND": lambda *a: not all(a), "NOR": lambda *a: not any(a),
    "TRUE": True, "FALSE": False,
}


def to_python(s: str) -> str:
    """Infix Boolean spelling -> Python. Function spelling needs no change.

    `.strip()` matters: a formula beginning `!X` becomes ` not X`, and the
    leading space is an IndentationError at compile time. That mistake scored
    376 evaluable nodes as failures on the first run of this analysis.
    """
    s = s.replace("&&", "&").replace("||", "|")
    return s.replace("&", " and ").replace("|", " or ").replace("!", " not ").strip()


def truth_table(expr: str, ins: list[str]) -> list[bool]:
    py = to_python(expr)
    names = {t for t in IDENT.findall(py)} - set(FUNCS) - {"and", "or", "not"}
    unknown = sorted(names - set(ins))
    if unknown:
        raise ValueError(f"UNDECLARED_VARS {unknown[:3]}")
    if len(ins) > MAX_ARITY:
        raise ValueError(f"ARITY_GT_{MAX_ARITY}")
    code = compile(py, "<logic>", "eval")
    return [bool(eval(code, {"__builtins__": {}},          # noqa: S307
                      {**FUNCS, **dict(zip(ins, bits))}))
            for bits in itertools.product([False, True], repeat=len(ins))]


def classify(entry, logic: str, ins: list[str]) -> str:
    if entry is None:
        return "no-gate-entry"
    gate = entry.get("gate") if isinstance(entry, dict) else entry
    if gate == "INPUT" or not ins:
        return "source"
    if gate == "IDENTITY":
        return "identity"
    if LEVEL.search(logic):
        return "multi-valued"
    if THRESH.search(logic):
        return "threshold"
    try:
        truth_table(logic, ins)
        return "derivable"
    except ValueError as e:
        return "undeclared-vars" if "UNDECLARED" in str(e) else "arity-too-large"
    except SyntaxError:
        return "unparseable"


def main() -> int:
    files = sorted(glob.glob(CORPUS))
    if not files:
        print(f"REFUSED: 0 networks under {CORPUS}. "
              "A corpus diagnostic over nothing is not a result.")
        return 2

    kept = []
    for f in files:
        d = json.load(open(f))
        if all(k in d and d[k] for k in ("cm", "gates", "nodes")):
            kept.append((f, d))
    total_nodes = sum(len(d["nodes"]) for _, d in kept)

    cat = collections.Counter()
    by_source = collections.defaultdict(collections.Counter)
    in_twelve = 0
    for _, d in kept:
        gates, logic = d["gates"], (d.get("logic") or {})
        src = d.get("source") or "unknown"
        for n in d["nodes"]:
            e = gates.get(n)
            gate = (e.get("gate") if isinstance(e, dict) else e) if e else None
            if gate in TWELVE:
                in_twelve += 1
                continue
            c = classify(e, (logic.get(n) or "").strip(),
                         (e or {}).get("inputs") or [])
            cat[c] += 1
            by_source[src][c] += 1

    outside = sum(cat.values())
    print(f"networks with cm+gates+nodes : {len(kept)}   (record: 170)")
    print(f"nodes over those networks    : {total_nodes}   (record: 5,204)")
    print(f"inside the twelve families   : {in_twelve}")
    print(f"outside the twelve families  : {outside}   "
          f"({100 * outside / total_nodes:.1f}%)   (record: 3,977 = 76.4%)")
    print(f"\nDECOMPOSITION of those {outside}:\n")
    order = ["derivable", "identity", "no-gate-entry", "multi-valued",
             "threshold", "undeclared-vars", "source", "arity-too-large",
             "unparseable"]
    for k in order:
        if cat[k]:
            print(f"   {k:<18}{cat[k]:>6}   {100 * cat[k] / outside:5.1f}%")

    derivable = cat["derivable"] + cat["identity"]
    blocked = cat["multi-valued"] + cat["threshold"]
    nofunc = cat["no-gate-entry"] + cat["source"]
    print(f"\n   DERIVABLE TODAY                {derivable:>6}   "
          f"{100 * derivable / outside:5.1f}%   truth table built, or y = x")
    print(f"   GENUINELY BLOCKED             {blocked:>6}   "
          f"{100 * blocked / outside:5.1f}%   multi-valued or free threshold")
    print(f"   NO UPDATE FUNCTION TO DERIVE  {nofunc:>6}   "
          f"{100 * nofunc / outside:5.1f}%   source nodes, or absent from gates")
    print(f"   DATA DEFECT                   {cat['undeclared-vars']:>6}   "
          f"{100 * cat['undeclared-vars'] / outside:5.1f}%   formula names "
          f"variables not in its own inputs")

    print(f"\n   blocked as a fraction of the full corpus: "
          f"{blocked}/{total_nodes} = {100 * blocked / total_nodes:.1f}% "
          f"(the record carries 76.4%)")

    print("\nby source (multi-valued / threshold / derivable):")
    for s, c in sorted(by_source.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"   {s:<28}{c['multi-valued']:>5} {c['threshold']:>6} "
              f"{c['derivable'] + c['identity']:>7}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
