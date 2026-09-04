#!/usr/bin/env python3
"""AUDIT03/R4.1 — what does a thirteenth family actually buy?

The plan asks: "what fraction of the AND/OR/NOT CUSTOM formulas does a
REGULATORY_DNF closed form reproduce, elementwise?"

That question has a trivial answer and asking it as posed would repeat a defect
this audit already found once. REGULATORY_DNF, as implemented in
index-deconvolution/src/causalbool.py:137, is an UNRESTRICTED disjunction of
activator/inhibitor clauses. Unrestricted DNF is functionally complete: every
Boolean function over d inputs is a DNF, one clause per minterm in the worst
case. So the elementwise reproduction rate is 100% BY CONSTRUCTION, for exactly
the reason P9 rejected the 256/256 ECA figure -- a criterion no candidate can
fail measures the criterion, not the candidate.

So the measurement is split into the two questions that CAN come out either way:

  A  PARSE COVERAGE -- the real gate. Can the formula be turned into a Boolean
     truth table at all? A formula is Boolean-evaluable iff every identifier in
     it resolves to a node of its own network. This is where the corpus
     actually resists: level-indexed references like `Cdc14:1` and threshold
     terms like `GEQ(x, theta)` are not Boolean variables, and a filter that
     only excludes the latter (as AUDIT03/R1.3's first pass did) lets the
     former through.

  B  COMPACTNESS -- the question that decides whether family 13 pays. Since
     every parsed formula is SOME DNF, the number that matters is HOW MANY
     CLAUSES, measured against the per-in-degree threshold s_max derived in
     R1.3: the largest clause count at which the schema field still beats a raw
     truth table. Below it the family pays for that node; above it, it loses.

  C  THE NET, in bits, summed only over nodes where it is actually positive,
     with the cost of the wider catalogue charged against it.

CONTROL. Parsing is checked, not trusted: the identifiers a formula references
must match the connected-input set recorded in the adjacency matrix. A formula
that parses but references different nodes than `cm` says is a data
inconsistency, and is reported rather than silently evaluated.

Run:
    venv/bin/python audit/AUDIT03_R4_thirteenth_family/measure_regulatory_dnf_coverage.py
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
sys.path.insert(0, str(ROOT / "index-deconvolution" / "src"))

import description_lengths as dl                    # noqa: E402
from deconvolution import minimal_dnf               # noqa: E402
from causalbool import apply_gate                  # noqa: E402

LINE = "-" * 78
CANONICAL = {"AND", "OR", "XOR", "NAND", "NOR", "XNOR", "NOT",
             "IMPLIES", "NIMPLIES", "MAJORITY", "KOFN", "CANALISING"}
# Guard: Quine-McCluskey is O(m^2) per round in the number of surviving terms.
# A parity-like table at d=13 has 4096 minterms and does not finish. Nodes above
# this are reported as NOT ATTEMPTED rather than left to hang or quietly dropped.
MINTERM_CAP = 512

TOKEN = re.compile(r"\s*(\(|\)|,|&&|\|\||&|\||!|~|[A-Za-z_][A-Za-z_0-9:.\-]*)")


def part(t: str) -> None:
    print(f"\n{LINE}\n{t}\n{LINE}")


def tokenize(s: str) -> list[str]:
    out, i = [], 0
    while i < len(s):
        m = TOKEN.match(s, i)
        if not m:
            if s[i].isspace():
                i += 1
                continue
            raise ValueError(f"unlexable character {s[i]!r}")
        out.append(m.group(1))
        i = m.end()
    return out


class Parser:
    """Boolean formulas in the two syntaxes the corpus actually uses:
    infix (`A & B & !C`, `(X | Y) & !Z`) and prefix (`OR(AND(NOT(a), b), c)`).
    Anything else raises, which is the point -- refusal is a result."""

    def __init__(self, toks: list[str]):
        self.t, self.i = toks, 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self, x=None):
        v = self.t[self.i]
        if x is not None and v != x:
            raise ValueError(f"expected {x!r}, got {v!r}")
        self.i += 1
        return v

    def parse(self):
        e = self.or_()
        if self.i != len(self.t):
            raise ValueError(f"trailing tokens at {self.t[self.i:]}")
        return e

    def or_(self):
        e = self.and_()
        while self.peek() in ("|", "||"):
            self.take()
            e = ("or", e, self.and_())
        return e

    def and_(self):
        e = self.not_()
        while self.peek() in ("&", "&&"):
            self.take()
            e = ("and", e, self.not_())
        return e

    def not_(self):
        if self.peek() in ("!", "~"):
            self.take()
            return ("not", self.not_())
        return self.atom()

    def atom(self):
        tok = self.peek()
        if tok == "(":
            self.take("(")
            e = self.or_()
            self.take(")")
            return e
        name = self.take()
        if self.peek() == "(":                     # prefix form NAME(a, b, ...)
            self.take("(")
            args = []
            if self.peek() != ")":
                args.append(self.or_())
                while self.peek() == ",":
                    self.take(",")
                    args.append(self.or_())
            self.take(")")
            up = name.upper()
            if up == "NOT":
                if len(args) != 1:
                    raise ValueError("NOT arity")
                return ("not", args[0])
            if up in ("AND", "OR"):
                if not args:
                    raise ValueError(f"{up} arity")
                e = args[0]
                for a in args[1:]:
                    e = (up.lower(), e, a)
                return e
            raise ValueError(f"unsupported function {name}")
        return ("var", name)


def ev(node, env: dict) -> int:
    k = node[0]
    if k == "var":
        if node[1] not in env:
            raise KeyError(node[1])
        return env[node[1]]
    if k == "not":
        return 1 - ev(node[1], env)
    if k == "and":
        return ev(node[1], env) & ev(node[2], env)
    if k == "or":
        return ev(node[1], env) | ev(node[2], env)
    raise ValueError(k)


def variables(node) -> set[str]:
    if node[0] == "var":
        return {node[1]}
    if node[0] == "not":
        return variables(node[1])
    return variables(node[1]) | variables(node[2])


def s_max_for(d: int, n: int) -> int:
    """R1.3's threshold, recomputed here so the two cannot drift apart."""
    k = min(d, n)
    lut = math.log2(n + 1) + math.log2(max(1, math.comb(n, d))) + float(2 ** d)
    per = math.log2(n + 1) + math.log2(max(1, math.comb(n, k))) + k
    s = 0
    while dl._gamma_len(s + 2) + (s + 1) * per <= lut and s < 4096:
        s += 1
    return s


def main() -> int:
    print("AUDIT03/R4.1 — what a thirteenth family actually buys")
    print("\nNOTE ON THE QUESTION. REGULATORY_DNF is UNRESTRICTED DNF, hence")
    print("functionally complete, so 'what fraction does it reproduce'")
    print("is 100% by construction and measures nothing. The two questions")
    print("below can come out either way.")

    rows, incons = [], []
    for path in sorted((ROOT / "data" / "bio" / "processed").glob("*.json")):
        net = json.loads(path.read_text())
        if not all(k in net for k in ("cm", "gates", "nodes")):
            continue
        nodes, cm, gates = net["nodes"], net["cm"], net.get("gates", {})
        logic = net.get("logic", {}) or {}
        n = len(nodes)
        nodeset = set(nodes)
        for i, node in enumerate(nodes):
            gate = (gates.get(node) or {}).get("gate", "INPUT")
            if gate in CANONICAL:
                continue
            f = logic.get(node, "") or ""
            d = sum(cm[i]) if i < len(cm) else 0
            rec = {"network": net.get("name", path.stem), "node": node,
                   "gate": gate, "d": d, "n": n, "formula": f,
                   "status": None, "clauses": None}
            if not f:
                rec["status"] = "no formula"
                rows.append(rec)
                continue
            try:
                ast = Parser(tokenize(f)).parse()
            except Exception as exc:
                rec["status"] = "unparsable"
                rec["reason"] = f"{type(exc).__name__}: {exc}"[:80]
                rows.append(rec)
                continue
            vs = variables(ast)
            unknown = vs - nodeset
            if unknown:
                rec["status"] = "identifier not a node"
                rec["reason"] = ", ".join(sorted(unknown))[:80]
                rows.append(rec)
                continue
            # CONTROL: the formula's variables must be the recorded inputs.
            recorded = {nodes[j] for j in range(min(n, len(cm[i])))
                        if cm[i][j] == 1}
            if vs != recorded:
                incons.append({"network": rec["network"], "node": node,
                               "formula_vars": sorted(vs),
                               "cm_inputs": sorted(recorded)})
            support = sorted(vs)
            dd = len(support)
            if dd > 20:
                rec["status"] = "support too large"
                rows.append(rec)
                continue
            tt = []
            try:
                for y in range(2 ** dd):
                    env = {v: (y >> b) & 1 for b, v in enumerate(support)}
                    tt.append(ev(ast, env))
            except Exception:
                rec["status"] = "unevaluable"
                rows.append(rec)
                continue
            rec["d_formula"] = dd
            if sum(tt) > MINTERM_CAP:
                rec["status"] = "not attempted (minterms > cap)"
                rows.append(rec)
                continue
            cl = minimal_dnf(tt)
            rec["clauses"] = len(cl)
            # D: the elementwise check the plan asked for, MEASURED. Feed the
            # clause list to the actual REGULATORY_DNF implementation and
            # compare against the parsed truth table, cell by cell.
            got = [apply_gate("REGULATORY_DNF",
                              [(y >> b) & 1 for b in range(dd)],
                              {"clauses": cl}) for y in range(2 ** dd)]
            rec["elementwise_exact"] = (got == tt)
            # NEGATIVE CONTROL: drop one literal from the first clause. Unless
            # the clause was empty, the cover must widen and the check must fail.
            if cl and (cl[0]["activators"] or cl[0]["inhibitors"]):
                bad = [dict(c) for c in cl]
                if bad[0]["activators"]:
                    bad[0] = {"activators": bad[0]["activators"][1:],
                              "inhibitors": bad[0]["inhibitors"]}
                else:
                    bad[0] = {"activators": bad[0]["activators"],
                              "inhibitors": bad[0]["inhibitors"][1:]}
                bad_got = [apply_gate("REGULATORY_DNF",
                                      [(y >> b) & 1 for b in range(dd)],
                                      {"clauses": bad}) for y in range(2 ** dd)]
                rec["control_fires"] = (bad_got != tt)
            rec["status"] = "ok"
            rows.append(rec)

    part("A — PARSE COVERAGE, the real gate")
    tot = len(rows)
    by = {}
    for r in rows:
        by[r["status"]] = by.get(r["status"], 0) + 1
    print(f"  non-canonical nodes examined: {tot}")
    for k, v in sorted(by.items(), key=lambda x: -x[1]):
        print(f"    {k:<32}{v:>6}  {100*v/tot:5.1f}%")
    ok = [r for r in rows if r["status"] == "ok"]
    print(f"\n  Boolean-evaluable, elementwise: {len(ok)} of {tot} "
          f"({100*len(ok)/tot:.1f}%)")
    print("  Every one of these IS reproduced by REGULATORY_DNF exactly, because")
    print("  its minimal DNF is a REGULATORY_DNF clause list. That is a")
    print("  restatement of functional completeness and no evidence for the")
    print("  family; the evidence is in B.")

    print(f"\n  CONTROL — formula variables vs the adjacency matrix: "
          f"{len(incons)} inconsistencies")
    for x in incons[:3]:
        print(f"    {x['network']}/{x['node']}: formula {x['formula_vars']} "
              f"vs cm {x['cm_inputs']}")

    part("D — ELEMENTWISE, MEASURED rather than argued")
    exact = sum(1 for r in ok if r.get("elementwise_exact"))
    ctrl = [r for r in ok if "control_fires" in r]
    fired = sum(1 for r in ctrl if r["control_fires"])
    print(f"  REGULATORY_DNF reproduces the parsed truth table exactly:")
    print(f"    {exact} of {len(ok)} nodes, cell by cell over every 2^d input")
    print(f"  NEGATIVE CONTROL, one literal dropped from the first clause:")
    print(f"    gate detected the change in {fired} of {len(ctrl)} nodes")
    if exact != len(ok):
        print("    ^ NOT 100%: functional completeness is violated somewhere,")
        print("      which would be a defect in minimal_dnf or in apply_gate")
    if ctrl and fired != len(ctrl):
        print(f"    ^ {len(ctrl)-fired} nodes where corruption changed nothing;")
        print("      those clauses carry a redundant literal")

    part("B — COMPACTNESS, against R1.3's threshold")
    print(f"  {'d':>3}{'nodes':>7}{'median s':>10}{'max s':>7}"
          f"{'s_max':>7}{'pays':>7}{'':>3}")
    pays_tot = loses_tot = 0
    per_d = {}
    for d in sorted({r["d_formula"] for r in ok}):
        grp = [r for r in ok if r["d_formula"] == d]
        ns = sorted(r["n"] for r in grp)
        med_n = ns[len(ns) // 2]
        thr = s_max_for(d, med_n)
        ss = sorted(r["clauses"] for r in grp)
        pays = sum(1 for r in grp if r["clauses"] <= s_max_for(d, r["n"]))
        pays_tot += pays
        loses_tot += len(grp) - pays
        per_d[d] = {"nodes": len(grp), "median_s": ss[len(ss)//2],
                    "max_s": ss[-1], "s_max_at_median_n": thr, "pays": pays}
        print(f"  {d:>3}{len(grp):>7}{ss[len(ss)//2]:>10}{ss[-1]:>7}"
              f"{thr:>7}{pays:>7}")
    print(f"\n  nodes where family 13 is CHEAPER than a raw table: "
          f"{pays_tot} of {len(ok)} ({100*pays_tot/max(1,len(ok)):.1f}%)")
    print(f"  nodes where it is DEARER: {loses_tot}")

    part("C — THE NET, in bits")
    saved = 0.0
    for r in ok:
        n, d, s = r["n"], r["d_formula"], r["clauses"]
        k = min(d, n)
        lut = math.log2(n+1) + math.log2(max(1, math.comb(n, d))) + 2 ** d
        per = math.log2(n+1) + math.log2(max(1, math.comb(n, k))) + k
        sch = dl._gamma_len(s + 1) + s * per
        if sch < lut:
            saved += lut - sch
    all_nodes = sum(1 for _ in (ROOT / "data" / "bio" / "processed").glob("*.json"))
    corpus_nodes = 5204
    cost = (math.log2(13) - math.log2(12)) * corpus_nodes
    print(f"  gross saving on the nodes where it pays : {saved:,.1f} bits")
    print(f"  cost of widening the catalogue          : {cost:,.1f} bits")
    print(f"  NET                                     : {saved - cost:,.1f} bits")
    print("\n  This supersedes the 58,217-bit figure, which the plan forbade")
    print("  quoting until this fraction was known. It is now known.")

    out = {"examined": tot, "status_counts": by,
           "elementwise_exact": exact, "elementwise_control_fired": fired,
           "elementwise_control_n": len(ctrl),
           "boolean_evaluable": len(ok),
           "cm_formula_inconsistencies": len(incons),
           "inconsistency_examples": incons[:20],
           "by_in_degree": per_d,
           "nodes_where_family13_pays": pays_tot,
           "nodes_where_family13_loses": loses_tot,
           "gross_saving_bits": saved, "catalogue_cost_bits": cost,
           "net_bits": saved - cost}
    (HERE / "regulatory_dnf_coverage.json").write_text(json.dumps(out, indent=1))
    print(f"\nwritten: {HERE / 'regulatory_dnf_coverage.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
