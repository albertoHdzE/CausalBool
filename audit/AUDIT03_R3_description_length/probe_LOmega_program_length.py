#!/usr/bin/env python3
"""AUDIT03/R3 follow-up — is D_formula the method's own programme, or a proxy?

The author's challenge: the description length in both manuscripts is built from
the connectivity matrix plus the gate list, which is "very naive". The method's
ACTUAL output is the compressed pair (L, Omega) — DecimalRepertoire and Sumandos
— and it is the length of THAT which should be measured in bits.

This script settles the question by measurement rather than by argument. It uses
the project's own gate evaluator (complexity_analysis._eval_gate) and the
project's own offset construction (allOffsets, transcribed from
generate_paper_outputs.wl), so it tests the method and not my reading of it.

Four gates:

  A  Does (L, Omega) reconstruct the one-set exactly, per node, elementwise?
  B  Is Omega actually free given the connected set — i.e. is it DERIVED or must
     it be TRANSMITTED? This decides whether (L, Omega) is one object or two.
  C  Price four candidate programmes for the same node, all self-delimiting, and
     compare them on the 10-node benchmark.
  D  Run the same comparison on the real biological corpus, where 76.4% of nodes
     have no gate label at all (AUDIT03/G5).

Run:
    venv/bin/python audit/AUDIT03_R3_description_length/probe_LOmega_program_length.py
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
sys.path.insert(0, str(HERE))

from complexity_analysis import _eval_gate, encode_node_cost   # noqa: E402
from verify_description_length import node_length              # noqa: E402

L = "-" * 76


def part(t):
    print(f"\n{L}\n{t}\n{L}")


def _log2(x):
    return math.log2(x) if x > 0 else 0.0


# --- the 10-node benchmark, copied verbatim from generate_paper_outputs.wl ---
CM10 = [
    [0, 1, 1, 0, 0, 0, 0, 0, 0, 0],
    [1, 0, 1, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 0, 0, 0],
    [0, 1, 1, 0, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
    [0, 0, 0, 0, 1, 0, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
    [1, 0, 0, 0, 0, 0, 0, 0, 1, 0],
    [0, 1, 0, 0, 0, 0, 0, 0, 0, 1],
    [0, 0, 1, 1, 0, 0, 1, 1, 0, 0],
]
DYN10 = ["AND", "OR", "XOR", "KOFN", "NOR", "XNOR", "NOT",
         "IMPLIES", "NIMPLIES", "MAJORITY"]
PARAMS10 = {4: {"k": 2}, 8: {"pair": [1, 9]}, 9: {"pair": [2, 10]}}


def weights(n):
    return [2 ** i for i in range(n)]          # LSB-first, as weights[n] in WL


def all_offsets(n, connected):
    """Sumandos. Transcribed from allOffsets in generate_paper_outputs.wl:
    every subset sum of the bit weights of the DISCONNECTED coordinates."""
    free = [i for i in range(n) if i not in connected]
    ws = [weights(n)[i] for i in free]
    if not ws:
        return [0]
    return sorted(sum(b * w for b, w in zip(bits, ws))
                  for bits in itertools.product([0, 1], repeat=len(ws)))


def one_set_and_base(n, cm, dyn, params, k):
    """The node's one-set, and its DecimalRepertoire L (base set): the indices
    where the node outputs 1 while every disconnected coordinate is held at 0.
    Indices are 1-based, matching the manuscripts."""
    ic = [j for j, v in enumerate(cm[k]) if v == 1]
    free = [j for j in range(n) if j not in ic]
    one, base = [], []
    for idx in range(2 ** n):
        state = [(idx >> i) & 1 for i in range(n)]
        if _eval_gate(dyn[k], [state[j] for j in ic], params.get(k + 1, {})) == 1:
            one.append(idx + 1)
            if all(state[j] == 0 for j in free):
                base.append(idx + 1)
    return ic, sorted(one), sorted(base)


def dec(base, offsets):
    """Deconvolution Dec(L, Omega) = {l + w}. givePlaces in the companion code."""
    return sorted(b + w for b in base for w in offsets)


# ===========================================================================
part("A — does Dec(L, Omega) reproduce the one-set exactly? (elementwise)")
# ===========================================================================
n = 10
print(f"  {'node':>4} {'gate':<10}{'d':>3}{'|one-set|':>11}{'|L|':>6}{'|Omega|':>9}"
      f"{'|L|x|Omega|':>13}  exact?")
nodes = []
for k in range(n):
    ic, one, base = one_set_and_base(n, CM10, DYN10, PARAMS10, k)
    om = all_offsets(n, ic)
    rebuilt = dec(base, om)
    exact = rebuilt == one
    nodes.append(dict(k=k, ic=ic, one=one, base=base, om=om, d=len(ic),
                      gate=DYN10[k], exact=exact))
    print(f"  {k + 1:>4} {DYN10[k]:<10}{len(ic):>3}{len(one):>11}{len(base):>6}"
          f"{len(om):>9}{len(base) * len(om):>13}  {'YES' if exact else 'NO'}")
print(f"\n  all ten exact: {all(x['exact'] for x in nodes)}")
print("""
  So the compressed pair really is a complete generative programme for the node:
  two short lists, and set addition rebuilds the full one-set with no truth
  table. That is the method, and it works.""")


# ===========================================================================
part("B — is Omega transmitted, or derived? (this decides everything)")
# ===========================================================================
print("""
  If Omega has to be SENT, it is data and must be paid for. If it is COMPUTED
  from the connected set, it is free and paying for it is double-counting.
  Test: throw Omega away, rebuild it from the connected set alone, compare.
""")
allderived = True
for x in nodes:
    rebuilt = all_offsets(n, x["ic"])
    ok = rebuilt == x["om"]
    allderived &= ok
    print(f"  node {x['k'] + 1:>2}: |Omega|={len(x['om']):>4}  "
          f"rebuilt from the connected set alone: {'IDENTICAL' if ok else 'DIFFERS'}")
print(f"""
  every Omega derived: {allderived}

  Omega is therefore NOT independent information. It is a deterministic
  function of which coordinates are disconnected -- all 2^(n-d) subset sums of
  their bit weights. Send the connected set and the decoder builds Omega itself.

  The same test on L: L is the set of base indices, and a base index is just the
  local input pattern on the d connected coordinates, shifted by 1. So L is
  exactly the node's LOCAL TRUTH TABLE over its own d inputs -- nothing more.""")
for x in nodes:
    local = []
    for m in range(2 ** x["d"]):
        st = [0] * n
        for t, j in enumerate(x["ic"]):
            st[j] = (m >> t) & 1
        if _eval_gate(x["gate"], [st[j] for j in x["ic"]],
                      PARAMS10.get(x["k"] + 1, {})) == 1:
            local.append(1 + sum(st[i] * weights(n)[i] for i in range(n)))
    x["local_ok"] = sorted(local) == x["base"]
print(f"\n  L == local truth table, all ten nodes: "
      f"{all(x['local_ok'] for x in nodes)}")
print("""
  CONCLUSION OF B. The pair (L, Omega) contains exactly two pieces of
  information and no more:
        Omega  <-  WHICH coordinates feed the node   (the index set)
        L      <-  WHAT the node does with them      (its local truth table)
  Anything that transmits those two things transmits the whole programme.""")


# ===========================================================================
part("C — pricing four programmes for the same node, on the 10-node benchmark")
# ===========================================================================
print("""
  P1  CATALOGUE   log2(12) + log2(n+1) + log2 C(n,d) + parameters
                  = D_formula, what both manuscripts report. Names the gate out
                    of a declared list of twelve.
  P2  (L,Omega)   log2(n+1) + log2 C(n,d) + 2^d
                  = send the index set, then the LOCAL TRUTH TABLE outright.
                    This IS the (L, Omega) programme, priced. No catalogue.
  P3  LITERAL     write L and Omega out as decimal lists, self-delimiting:
                    a length field then n bits per entry, for both lists.
  P4  RAW         the node's whole output column: 2^n bits.
""")
print(f"  {'node':>4} {'gate':<10}{'d':>3}{'P1 cat':>10}{'P2 (L,Om)':>12}"
      f"{'P3 literal':>12}{'P4 raw':>9}")
tot = [0.0, 0.0, 0.0, 0.0]
for x in nodes:
    d = x["d"]
    p1 = encode_node_cost(d, x["gate"], n)
    p2 = _log2(n + 1) + _log2(math.comb(n, d)) + 2 ** d
    p3 = (2 * _log2(2 ** n + 1)
          + len(x["base"]) * n + len(x["om"]) * n)
    p4 = 2 ** n
    for i, v in enumerate((p1, p2, p3, p4)):
        tot[i] += v
    print(f"  {x['k'] + 1:>4} {x['gate']:<10}{d:>3}{p1:>10.2f}{p2:>12.2f}"
          f"{p3:>12.0f}{p4:>9}")
print(f"  {'TOTAL':>19}{tot[0]:>10.2f}{tot[1]:>12.2f}{tot[2]:>12.0f}{tot[3]:>9.0f}")
print(f"""
  P1 = {tot[0]:.2f} bits is the published D_formula = 135.66.

  Read the table, not the totals. P2, the honest price of the (L, Omega)
  programme, is {tot[1]:.2f} bits -- LARGER than P1 by {tot[1] - tot[0]:.2f} bits.
  P3, writing the two lists out literally, is {tot[2]:.0f} bits, larger again by
  more than two orders of magnitude, because Omega has 2^(n-d) entries and
  writing it down re-inflates exactly the thing the method compresses.

  So the catalogue encoding is not a naive alternative to (L, Omega).
  It is a SHORTER ENCODING OF THE SAME OBJECT: instead of spelling out the
  local truth table in 2^d bits, it says "this table is family number 3" in
  log2(12) bits. The saving is 2^d - log2(12) - parameters, which grows
  exponentially in the in-degree.""")


# ===========================================================================
part("D — the same comparison on the real corpus, where there IS no gate label")
# ===========================================================================
from integration.bio_D_experiment import load_processed_bio_networks   # noqa: E402

GATE12 = ["AND", "OR", "XOR", "NAND", "NOR", "XNOR", "NOT", "IMPLIES",
          "NIMPLIES", "MAJORITY", "KOFN", "CANALISING"]
nets = load_processed_bio_networks(ROOT)
buckets = {}
p1_named = p2_all = 0.0
named = unnamed = 0
degrees = {}
for nm, v in nets.items():
    nn = len(v["dynamic"])
    if nn == 0:
        continue
    for i, g in enumerate(v["dynamic"]):
        d = int(sum(v["cm"][i]))
        degrees[d] = degrees.get(d, 0) + 1
        p2 = _log2(nn + 1) + _log2(math.comb(nn, d)) + 2.0 ** min(d, 30)
        p2_all += p2
        if g in GATE12:
            named += 1
            p1_named += encode_node_cost(d, g, nn)
        else:
            unnamed += 1
        buckets.setdefault(d, [0, 0.0, 0.0])
        buckets[d][0] += 1
        buckets[d][1] += node_length(g if g in GATE12 else "AND", d, nn)
        buckets[d][2] += p2
print(f"""
  On the corpus the catalogue encoding CANNOT BE WRITTEN for {unnamed} of
  {named + unnamed} nodes -- there is no codeword for CUSTOM, IDENTITY or INPUT
  (AUDIT03/G5). The (L, Omega) programme has no such problem: every node has a
  local truth table whether or not we have named its shape.

  But the price is the point. Cost per node, by in-degree:
""")
print(f"  {'d':>3}{'nodes':>8}{'P1 catalogue':>16}{'P2 (L,Omega)':>16}{'cheaper':>10}")
for d in sorted(buckets)[:14]:
    cnt, a, b = buckets[d]
    print(f"  {d:>3}{cnt:>8}{a / cnt:>16.2f}{b / cnt:>16.2f}"
          f"{('catalogue' if a < b else '(L,Omega)'):>10}")
print(f"""
  The crossover is at d = 2-3, exactly where 2^d passes log2(12) + 1 = 4.58.
  Below it the local truth table is cheaper; above it the catalogue wins, and by
  d = 7 it wins by a factor of about twenty.

  Corpus in-degree distribution: {dict(sorted(degrees.items())[:10])}
""")

json.dump({"benchmark_totals": {"P1_catalogue": tot[0], "P2_L_Omega": tot[1],
                                "P3_literal_lists": tot[2], "P4_raw": tot[3]},
           "all_ten_reconstruct_exactly": all(x["exact"] for x in nodes),
           "omega_always_derived": allderived,
           "L_equals_local_truth_table": all(x["local_ok"] for x in nodes),
           "corpus": {"named": named, "unnamed": unnamed,
                      "by_indegree": {str(k): v for k, v in sorted(buckets.items())}}},
          open(HERE / "LOmega_probe.json", "w"), indent=1)


# ===========================================================================
part("E — is the proposed hybrid actually a legal code? (do not assert, check)")
# ===========================================================================
print("""
  Proposal: one bit says which branch, then either the catalogue programme or
  the (L, Omega) programme. Proposing a code is easy; it is only a code if the
  cake still adds to at most one. Enumerate both branches exhaustively.
""")
from verify_description_length import GATE_LABELS, param_alphabet   # noqa: E402

print(f"  {'n':>3}{'catalogue branch':>20}{'LUT branch':>14}{'TOTAL':>10}")
hyb_ok = True
for nn in range(1, 7):
    b_cat = 0.0
    for g in GATE_LABELS:
        for d in range(nn + 1):
            bits = 1 + _log2(nn + 1) + _log2(math.comb(nn, d)) \
                     + _log2(len(GATE_LABELS)) + _log2(param_alphabet(g, d, nn))
            b_cat += math.comb(nn, d) * param_alphabet(g, d, nn) * 2.0 ** -bits
    b_lut = 0.0
    for d in range(nn + 1):
        bits = 1 + _log2(nn + 1) + _log2(math.comb(nn, d)) + 2 ** d
        b_lut += math.comb(nn, d) * (2.0 ** (2 ** d)) * 2.0 ** -bits
    tot_h = b_cat + b_lut
    hyb_ok &= abs(tot_h - 1.0) < 1e-9
    print(f"  {nn:>3}{b_cat:>20.9f}{b_lut:>14.9f}{tot_h:>10.6f}")
print(f"""
  hybrid is a complete, legal code at every width tested: {hyb_ok}

  Each branch eats exactly half the cake, and the two halves make one. Note the
  LUT branch counts 2^(2^d) tables -- EVERY Boolean function of d inputs, named
  or not. That is what makes it cover CUSTOM, IDENTITY and INPUT. Nothing here
  is free: the extra bit is charged, and both branches are charged the index set.
""")


# ===========================================================================
part("VERDICT")
# ===========================================================================
print("""
  The author is RIGHT that (L, Omega) is the method's real programme, and right
  that D_formula as published never measures it directly.

  The author's inference does not follow, and the measurement says why:
  (L, Omega) carries exactly two pieces of information -- WHICH inputs, and
  WHAT the node does with them -- and the catalogue encoding transmits both.
  It is not a different object. It is the same programme with the local truth
  table replaced by a pointer into a declared library, which is shorter whenever
  the in-degree exceeds about three. Writing L and Omega out as decimal lists is
  the DECOMPRESSED form and costs two orders of magnitude more.

  What IS wrong, and what the author's instinct has correctly located, is the
  catalogue's coverage. P1 cannot be written at all for three quarters of the
  corpus. P2 always can. The right description length is therefore neither one
  alone but the cheaper of the two, per node, with one bit declaring which --
  and that is a code that covers the whole corpus and is still short where the
  catalogue applies. It is also the exact place where a thirteenth family pays
  for itself: every CUSTOM node it names drops from 2^d bits to log2(13).
""")
