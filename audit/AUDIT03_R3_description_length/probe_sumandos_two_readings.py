#!/usr/bin/env python3
"""AUDIT03/R3 — TWO INCOMPATIBLE READINGS OF Omega (sumandos) LIVE IN THIS PROJECT.

The author's correction, 2026-09-03: Omega is NOT "the disconnected coordinates".
I asserted that it was, in a commit message and in a recall decision, and I was
wrong. The correct reading was established on 2026-07-09 and is recorded in
index-deconvolution/bitacora/11_gate_confusion_arity_schemata.md:

    "Each clause of the index-set rule is a schema in Holland's sense: it fixes
     some inputs and leaves the rest as don't-cares, which are exactly the
     sumandos. Probe D recovers rule 110 as three schemata, 01*, 10* and *10
     over its three inputs, whose free positions are the sumandos."

Rule 110 has THREE inputs and ALL THREE ARE CONNECTED. Its don't-cares are
therefore among the CONNECTED coordinates. Under the reading I used they would
not exist at all.

This script establishes, by measurement:
  R1  the two readings genuinely differ, on rule 110 and on ordinary gates;
  R2  the narrow reading is what BOTH manuscripts state, so this is a project
      defect and not merely my mistake;
  R3  the general reading compresses far more, and the gap GROWS with arity and
      with network size -- which is the author's "fractal" claim, quantified;
  R4  the schema normal form gives ONE description length, with no gate
      catalogue, no second branch and nothing Shannon-derived;
  R5  that length is a legal code (Kraft), checked rather than asserted.

Run:
    venv/bin/python audit/AUDIT03_R3_description_length/probe_sumandos_two_readings.py
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
sys.path.insert(0, str(ROOT / "index-deconvolution" / "src"))
sys.path.insert(0, str(ROOT / "papers" / "method" / "code" / "complexity_analysis"))

from deconvolution import minimal_dnf                      # noqa: E402  (project code)
from complexity_analysis import _eval_gate, encode_node_cost   # noqa: E402

LINE = "-" * 76


def part(t):
    print(f"\n{LINE}\n{t}\n{LINE}")


def _log2(x):
    return math.log2(x) if x > 0 else 0.0


def schema_str(clause, m):
    s = ["*"] * m
    for a in clause["activators"]:
        s[a] = "1"
    for b in clause["inhibitors"]:
        s[b] = "0"
    return "".join(s)


def local_tt(gate, d, params=None):
    """Truth table of a gate over its d connected inputs, LSB-first."""
    return [_eval_gate(gate, [(y >> i) & 1 for i in range(d)], params or {})
            for y in range(2 ** d)]


# ===========================================================================
part("R1 — rule 110: where are its don't-cares?")
# ===========================================================================
tt110 = [(110 >> b) & 1 for b in range(8)]
cl110 = minimal_dnf(tt110)
print(f"  rule 110 truth table (LSB-first): {tt110}   on-set size {sum(tt110)}")
print("\n  READING A — the one both manuscripts state:")
print("      'Omega enumerates the fillings of the DISCONNECTED coordinates'")
print("      rule 110 has 3 inputs and all 3 are connected, so")
print("      free coordinates = {}  ->  Omega = {0}  ->  NO COMPRESSION AT ALL.")
print(f"      L would have to list all {sum(tt110)} minterms outright.")
print("\n  READING B — the one recorded in bitacora 11 (2026-07-09):")
print("      'the don't-cares ARE the sumandos', taken over the rule's own inputs")
for c in cl110:
    print(f"      schema {schema_str(c, 3)}    free positions = "
          f"{[i for i in range(3) if schema_str(c, 3)[i] == '*']}  <- CONNECTED inputs")
print(f"      {len(cl110)} schemata instead of {sum(tt110)} minterms.")
print("""
  The two readings are not two descriptions of one thing. Under A the sumandos
  of rule 110 are the empty set; under B there are three of them and every one
  sits on a connected input. A cannot express B. The author is right, and the
  reading I used is the narrow one.""")


# ===========================================================================
part("R2 — which reading is written into the project?")
# ===========================================================================
print("""
  Narrow reading (Omega = disconnected coordinates only):
    papers/method/manuscript_computational/comp_paper.tex:471
      "Each shift corresponds to an assignment of the remaining coordinates
       -- those that do not feed the node"
    papers/method/manuscript_formal/method_paper.tex  (Dec operator)
      "the offset set S encodes the free (disconnected) coordinates"
    papers/method/manuscript_computational/generate_paper_outputs.wl:45
      allOffsets[n, connected] := ... free = Complement[Range[n], connected]

  General reading (Omega = the don't-cares of each schema, wherever they fall):
    index-deconvolution/bitacora/11_gate_confusion_arity_schemata.md:83
    index-deconvolution/src/deconvolution.py  minimal_dnf  (used above)

  So this is a PROJECT-WIDE inconsistency, not a slip in one commit. The
  implementation named allOffsets computes reading A and is the only one the
  manuscripts describe; reading B exists only in the deconvolution package and
  in the bitacora. Cleaning this up is a real task, listed at the end.""")


# ===========================================================================
part("R3 — the growth claim, quantified")
# ===========================================================================
print("""
  The author's claim: as the network grows, decimals and sumandos compress more
  and more. Test it on the object that grows -- the local rule's on-set versus
  the number of schemata needed to cover it.

  |L| narrow  = how many minterms reading A must list
  schemata    = how many templates reading B needs for the same on-set
""")
print(f"  {'gate':<10}{'d':>3}{'|on-set|':>10}{'|L| narrow':>12}{'schemata':>10}{'ratio':>9}")
growth = {}
for gate in ("OR", "AND", "MAJORITY", "XOR"):
    for d in (2, 3, 4, 6, 8, 10):
        tt = local_tt(gate, d)
        if sum(tt) == 0:
            continue
        cl = minimal_dnf(tt)
        growth[f"{gate}_{d}"] = (sum(tt), len(cl))
        print(f"  {gate:<10}{d:>3}{sum(tt):>10}{sum(tt):>12}{len(cl):>10}"
              f"{sum(tt) / len(cl):>9.1f}x")
print("""
  OR is the clean case: its on-set doubles with every extra input while its
  schema count grows by ONE. At d = 10 reading A lists 1023 minterms and reading
  B needs 10 templates. That is a hundredfold gap on a single node, and it opens
  exponentially. XOR is the opposite extreme -- no two of its minterms merge, so
  the schema count equals the on-set and no compression is available. That
  contrast is a real property of the gate, and a measure that cannot see it is
  not measuring the object.

  Now the second half of the claim: hold the rule fixed and grow the AMBIENT
  network. The pattern it generates in the full repertoire doubles each time a
  node is added, while the rule that generates it does not change at all.
""")
print(f"  {'n':>4}{'|one-set| of an OR(d=3) node':>32}{'schemata':>10}{'compression':>14}")
for n in (4, 6, 8, 10, 14, 18, 22):
    tt = local_tt("OR", 3)
    cl = minimal_dnf(tt)
    onesz = sum(tt) * 2 ** (n - 3)
    print(f"  {n:>4}{onesz:>32}{len(cl):>10}{onesz / len(cl):>14.0f}x")
print("""
  THAT is what "fractal" means here, and it is exactly what the author
  described: one short rule, self-replicated at every scale, with the
  compression ratio growing without bound as the ambient space grows. The rule
  is invariant; only the number of places it lands changes.""")


# ===========================================================================
part("R4 — ONE description length, from the schema normal form")
# ===========================================================================
print("""
  The author rejects a hybrid measure, and is right to: two branches with a
  selector bit is an admission that neither branch is the object. The schema
  normal form gives a single measure, and it needs no gate catalogue at all.

  A node is a LIST OF SCHEMATA over the n coordinates. To write one schema:

      log2(n+1)      how many coordinates this schema fixes  (its ORDER k)
      log2 C(n,k)    which coordinates they are
      k              their values, one bit each

  and to write the node, a self-delimiting count of how many schemata follow.
  Everything else -- the don't-cares, the offsets, the whole 2^(n-k) family of
  places the schema lands -- is REGENERATED by the decoder. It is never
  transmitted, because it is not information.

  Nothing here is Shannon. No frequency, no ensemble, no entropy. It is the
  length of the exact program that writes the pattern down.
""")


def elias_gamma_len(x):
    """Self-delimiting length for a positive integer."""
    return 2 * (x.bit_length() - 1) + 1 if x >= 1 else 1


def schema_normal_form_bits(tt, d, n):
    """One description length for a node: its schemata, written out."""
    if sum(tt) == 0:
        return elias_gamma_len(1)                    # 'zero schemata' marker
    cl = minimal_dnf(tt)
    bits = elias_gamma_len(len(cl) + 1)              # how many schemata follow
    for c in cl:
        k = len(c["activators"]) + len(c["inhibitors"])
        bits += _log2(n + 1) + _log2(math.comb(n, k)) + k
    return bits


print(f"  {'gate':<10}{'d':>3}{'D_formula (catalogue)':>24}{'D_schema (this)':>18}")
n = 10
for gate, d in (("AND", 2), ("OR", 2), ("XOR", 2), ("KOFN", 3),
                ("MAJORITY", 4), ("OR", 7), ("XOR", 7)):
    tt = local_tt(gate, d, {"k": 2} if gate == "KOFN" else None)
    a = encode_node_cost(d, gate, n)
    b = schema_normal_form_bits(tt, d, n)
    print(f"  {gate:<10}{d:>3}{a:>24.2f}{b:>18.2f}")
print("""
  D_schema is larger than D_formula on gates the catalogue happens to name, and
  that is correct and expected: a catalogue is a dictionary agreed in advance,
  and a dictionary is free information smuggled into the encoder. D_schema pays
  for everything it uses. It is the honest number.

  And unlike D_formula it can be written for EVERY node, including the 3,977 of
  5,204 corpus nodes labelled CUSTOM, IDENTITY or INPUT that the twelve-family
  catalogue cannot express at all.""")


# ===========================================================================
part("R5 — is D_schema a legal code? enumerate, do not assert")
# ===========================================================================
print("""
  A schema over n coordinates is drawn from an alphabet of exactly 3^n
  templates. Charging log2(n+1) + log2 C(n,k) + k bits for one is a uniform
  index into that alphabet, so the schema field's Kraft sum must be exactly 1.
""")
print(f"  {'n':>4}{'schema alphabet 3^n':>22}{'Kraft sum':>14}")
ok = True
for n in range(1, 9):
    s = 0.0
    for k in range(n + 1):
        bits = _log2(n + 1) + _log2(math.comb(n, k)) + k
        s += math.comb(n, k) * (2 ** k) * 2.0 ** -bits
    ok &= abs(s - 1.0) < 1e-9
    print(f"  {n:>4}{3 ** n:>22}{s:>14.9f}")
print(f"""
  every width sums to exactly one: {ok}

  (Count check: sum over k of C(n,k)*2^k = 3^n, which is the number of
  {{0,1,*}} templates. So the enumeration is over the real alphabet and not a
  convenient one.)

  The clause-count field is Elias gamma, whose Kraft sum is below 1 by
  construction, so the product code is legal.""")

json.dump({"rule110_narrow_omega": [0], "rule110_schemata":
           [schema_str(c, 3) for c in cl110],
           "growth": {k: {"onset": v[0], "schemata": v[1]}
                      for k, v in growth.items()},
           "schema_field_kraft_exact": ok},
          open(HERE / "sumandos_two_readings.json", "w"), indent=1)


# ===========================================================================
part("WHAT MUST BE CLEANED UP")
# ===========================================================================
print("""
  1. comp_paper.tex:471 and the three-level passage at :364 define Omega as the
     fillings of the DISCONNECTED coordinates. Narrow. Must be restated as the
     don't-cares of the schema, of which the disconnected coordinates are the
     special case that is always present.
  2. method_paper.tex's Dec definition says "the offset set S encodes the free
     (disconnected) coordinates". Same correction.
  3. generate_paper_outputs.wl:45 allOffsets, and its copies in
     corroboration_6node.wl and mixed_interaction_10node.wl, implement the
     narrow reading only. They are not wrong as code -- they compute a correct
     Omega for the disconnected part -- but they are NOT the general object and
     must not be presented as it.
  4. My commit c43d6e5 and recall decision #94 assert the narrow reading as
     theory. Both are wrong and are superseded by this file.
  5. GOVERNANCE needs a glossary entry fixing 'sumandos' so the narrow reading
     cannot be re-adopted by the next reader of allOffsets -- which is exactly
     how I adopted it.
""")
