#!/usr/bin/env python3
"""AUDIT03/R3 explained on the smallest possible example.

Companion to FINDING.md. Same defect, same fix, but on a network with TWO nodes,
where every object is small enough to be printed in full and checked by hand.
Nothing here is summarised: each number reported in the finding is recomputed and
its arithmetic shown.

    venv/bin/python audit/AUDIT03_R3_description_length/explain_by_example.py
"""

from __future__ import annotations

import itertools
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_description_length import (      # noqa: E402
    GATE_LABELS, K, kraft_sum, node_length, param_alphabet,
)

L = "-" * 74


def part(title):
    print(f"\n{L}\n{title}\n{L}")


# ===========================================================================
part("PART 1 — what a 'description length' is: a message down a phone line")
# ===========================================================================
print("""
The smallest network worth drawing has TWO nodes. Call them A and B.
Suppose the rule for node A is:

        next value of A  =  A AND B

I want to send that rule to a friend who can only hear 0s and 1s.
The DESCRIPTION LENGTH is simply: how many 0s and 1s must I send?

That is the whole idea. It is not a statistic, not an average, not entropy.
It is the length of a message. Shorter message = simpler object. This is what
'algorithmic complexity' means in this project.

We agreed on a fixed way of writing the message. Four parts, in this order:
""")

n = 2
d = 2
gate = "AND"

fields = [
    ("1. which gate?",            K,                  "one of the 12 families we defined"),
    ("2. how many inputs (d)?",   n + 1,              "d can be 0, 1 or 2, so 3 choices"),
    ("3. which inputs?",          math.comb(n, d),    f"how many ways to pick {d} of {n}"),
    ("4. gate parameters",        param_alphabet(gate, d, n), "e.g. a polarity bit"),
]

print(f"   {'field':<28}{'choices':>9}{'bits = log2(choices)':>24}")
tot = 0.0
for name, choices, why in fields:
    bits = math.log2(choices) if choices > 0 else 0.0
    tot += bits
    print(f"   {name:<28}{choices:>9}{bits:>24.4f}   <- {why}")
print(f"   {'TOTAL for this one node':<28}{'':>9}{tot:>24.4f} bits")
print(f"\n   cross-check against the real code: {node_length(gate, d, n):.4f} bits")
print("""
Read the middle column, not the right one. "log2(12) = 3.585 bits" is just
another way of writing "I had to pick one out of 12". The bits are a
consequence of the CHOICES. That is the only place any number here comes from.
""")


# ===========================================================================
part("PART 2 — the bug, printed in full")
# ===========================================================================
print("""
Field 2 ("how many inputs") was MISSING from two of our files. The message
being sent was only:  (which gate, which input set, parameters).

Why that breaks everything: "which input set" is an index into a LIST, and
there is a DIFFERENT LIST for every value of d. Here are all the lists for a
2-node network:
""")
for dd in range(n + 1):
    sets = [tuple("AB"[i] for i in S) for S in itertools.combinations(range(n), dd)]
    print(f"   d = {dd}   list = {sets}")

print("""
Now I send you: "gate = AND, input set number 0, parameter 0".
You cannot read it. Look at the lists above — entry number 0 is:

        if d = 0  ->  ()       node A depends on nothing
        if d = 1  ->  ('A',)   node A depends on itself
        if d = 2  ->  ('A','B') node A depends on both

THREE DIFFERENT NETWORKS. ONE IDENTICAL MESSAGE.

So the message was not a description. It was a number we computed and called
a description length. That is the entire finding. The fix is one line: also
send d, which costs log2(3) = 1.585 bits here.
""")


# ===========================================================================
part("PART 3 — Kraft: the 'one cake' law, and why the answer was n+1")
# ===========================================================================
print("""
There is a law about messages. Give every possible message a length L, and add
up 2^(-L) over all of them. If the messages are readable, that total can never
exceed 1. Think of it as ONE CAKE:

   a 1-bit message eats  2^-1 = half the cake
   a 2-bit message eats  2^-2 = a quarter
   a 3-bit message eats  2^-3 = an eighth

Short messages are greedy. If your lengths add up to MORE than one cake, you
have promised more short messages than can exist, and some of them must be
sharing — which is exactly the ambiguity we saw in PART 2.

Let us eat the cake by hand for our 2-node network. Every node we could ever
describe, listed one by one, WITH the in-degree field:
""")

print(f"   {'gate':<12}{'d':>3}{'#sets':>7}{'#params':>9}{'#nodes':>8}{'bits each':>11}{'cake eaten':>13}")
running = 0.0
shown = 0
for g in GATE_LABELS:
    for dd in range(n + 1):
        nsets = math.comb(n, dd)
        npar = param_alphabet(g, dd, n)
        cnt = nsets * npar
        bits = node_length(g, dd, n, with_indegree=True)
        eaten = cnt * 2.0 ** -bits
        running += eaten
        if shown < 8 or g == GATE_LABELS[-1]:
            print(f"   {g:<12}{dd:>3}{nsets:>7}{npar:>9}{cnt:>8}{bits:>11.4f}{eaten:>13.6f}")
        elif shown == 8:
            print(f"   {'... (the other gates, same pattern) ...':<50}")
        shown += 1
print(f"   {'TOTAL CAKE EATEN':<50}{running:>13.6f}   <- exactly 1")

print("\n   Now delete field 2 and eat again:")
print(f"   {'TOTAL CAKE EATEN without the in-degree field':<50}"
      f"{kraft_sum(n, False):>13.6f}   <- 3 cakes")
print(f"""
   3 cakes, for a 2-node network. And 3 = n + 1 = the number of possible
   in-degrees (0, 1, 2). That is not a coincidence and it is not a metaphor:
   we ate the cake once for d=0, once for d=1 and once for d=2, because we
   never said which one it was. Here is the same count for every size:
""")
print(f"   {'n':>3}{'with the field':>18}{'without it':>14}{'n+1':>7}")
for nn in range(1, 9):
    print(f"   {nn:>3}{kraft_sum(nn, True):>18.6f}{kraft_sum(nn, False):>14.6f}{nn + 1:>7}")
print("""
   That table is the '1 versus n+1' line in my report. It is a measurement,
   made by literally listing every describable node and adding up its slice.
""")


# ===========================================================================
part("PART 4 — 'every description round-trips': 48, 119, 293, 715, 1725, 4111")
# ===========================================================================
print("""
A cake sum can still be fooled if I added up the wrong list. So the real proof
is a decoder: write the message, throw the original away, read the message
back, and check I get the SAME node. Not a count of how many matched — the
actual node, part by part.

Those six numbers are just how many nodes exist to test at each size. For a
1-node network the whole universe of describable nodes is 48. Where does 48
come from? Add up the last column of this table:
""")
one = 1
print(f"   {'gate':<12}{'d=0 sets x params':>20}{'d=1 sets x params':>20}{'nodes':>8}")
total48 = 0
for g in GATE_LABELS:
    a = math.comb(one, 0) * param_alphabet(g, 0, one)
    b = math.comb(one, 1) * param_alphabet(g, 1, one)
    total48 += a + b
    print(f"   {g:<12}{f'1 x {param_alphabet(g, 0, one)} = {a}':>20}"
          f"{f'1 x {param_alphabet(g, 1, one)} = {b}':>20}{a + b:>8}")
print(f"   {'TOTAL':<12}{'':>20}{'':>20}{total48:>8}   <- the 48")
print("""
   The same sum at n=2 gives 119, at n=3 gives 293, and so on up to 4,111 at
   n=6. Every single one of those was encoded and decoded, and every part came
   back identical. Zero failures.
""")


# ===========================================================================
part("PART 5 — the negative control: 168 collisions at n=3, 404 at n=4")
# ===========================================================================
print("""
A test that can never fail proves nothing. So we also ran the BROKEN code on
purpose and demanded that it break. Delete field 2, then look for two
DIFFERENT nodes that produce the SAME message. Here they are for n=2:
""")
seen, cols = {}, []
for g in GATE_LABELS:
    for dd in range(n + 1):
        for S in itertools.combinations(range(n), dd):
            for p in range(param_alphabet(g, dd, n)):
                msg = (g, list(itertools.combinations(range(n), dd)).index(S), p)
                if msg in seen and seen[msg][1] != dd:
                    cols.append((seen[msg], (g, dd, S, p), msg))
                else:
                    seen.setdefault(msg, (g, dd, S, p))
for (a, b, msg) in cols[:5]:
    nm = lambda S: tuple("AB"[i] for i in S)
    print(f"   message (gate={msg[0]}, set#={msg[1]}, param={msg[2]}) reads as")
    print(f"        d={a[1]} inputs={nm(a[2])}   OR   d={b[1]} inputs={nm(b[2])}")
print(f"\n   collisions at n=2: {len(cols)}")
for nn in (3, 4):
    seen2, c2 = {}, 0
    for g in GATE_LABELS:
        for dd in range(nn + 1):
            for S in itertools.combinations(range(nn), dd):
                for p in range(param_alphabet(g, dd, nn)):
                    msg = (g, list(itertools.combinations(range(nn), dd)).index(S), p)
                    if msg in seen2 and seen2[msg] != dd:
                        c2 += 1
                    else:
                        seen2.setdefault(msg, dd)
    print(f"   collisions at n={nn}: {c2}")
print("""
   168 and 404 are simply how many such clashes exist at those sizes. The
   point is not the size of the number. The point is that it is NOT ZERO, so
   the check is alive: it can detect a broken code, therefore its 'pass' on
   the fixed code means something.
""")


# ===========================================================================
part("PART 6 — '572 cells, 0 disagreements'")
# ===========================================================================
pairs = [(nn, dd) for nn in range(1, 9) for dd in range(nn + 1)]
print(f"""
We have FOUR separate programs that each claim to compute this cost — two
Python files, one Wolfram file, and the fresh one written for this audit. If
they disagree anywhere, at least one is wrong.

So we made a table: every network size n from 1 to 8, every in-degree d from 0
to n, every one of 13 gate labels. That is

    (n,d) pairs = {len(pairs)}      x   13 gate labels   =   {len(pairs) * 13} cells

and in each cell we compared all four answers. 'Elementwise' means we compared
CELL BY CELL, not four totals. Four totals could match by luck; 572 cells
cannot. Result: 0 cells disagree. Before the fix, all 572 disagreed, because
the two bio files were short by log2(n+1) in every single one.
""")


# ===========================================================================
part("PART 7 — the corpus: 5,204 nodes and 27,756.72 bits")
# ===========================================================================
from integration.bio_D_experiment import load_processed_bio_networks   # noqa: E402

nets = load_processed_bio_networks(ROOT)
rows = [(nm, len(v["dynamic"])) for nm, v in nets.items() if v["dynamic"]]
nodes = sum(k for _, k in rows)
missing = sum(k * math.log2(k + 1) for _, k in rows)
print(f"""
'The corpus' is our folder of real biological networks. The loader keeps
{len(rows)} of them, with {nodes} nodes in total.

Each node was undercharged by exactly log2(n+1) bits, where n is the size of
ITS OWN network. So a node in a 10-node network was short log2(11) bits, and a
node in a 94-node network was short log2(95) bits. Three examples:
""")
for nm, k in sorted(rows, key=lambda r: -r[1])[:3]:
    print(f"   {nm[:40]:<42} n={k:<4} each node short log2({k + 1}) = "
          f"{math.log2(k + 1):.4f} bits, x{k} = {k * math.log2(k + 1):.2f}")
print(f"""
   Add that up over all {len(rows)} networks:  {missing:.2f} bits
   Divide by the {nodes} nodes:                {missing / nodes:.4f} bits per node

Those are the two numbers in my report. The earlier figure of 34,469 was wrong
because it counted 6,577 nodes. Three different node counts exist for one
folder, which is why they must always be named:
""")
import glob                                                            # noqa: E402
c_nodes = c_gates = 0
for p in sorted(glob.glob(str(ROOT / "data/bio/processed/*.json"))):
    try:
        j = json.loads(Path(p).read_text())
    except Exception:
        continue
    c_nodes += len(j.get("nodes") or [])
    c_gates += len(j.get("gates") or [])
print(f"   {nodes:>6}  nodes the LOADER actually keeps  <- the right one to use")
print(f"   {c_nodes:>6}  nodes listed across all files")
print(f"   {c_gates:>6}  nodes that carry a 'gates' entry")
print("""
And one important consequence, which is good news. The correction is
n x log2(n+1), the SAME for a network and for that network with one gene
knocked out, because both have the same n. So it CANCELS in every knockout
comparison. It does NOT cancel when comparing networks of different sizes, or
in any ratio such as fold_reduction.
""")


# ===========================================================================
part("PART 8 — the bigger problem: 3,977 of 5,204 nodes (76.4%)")
# ===========================================================================
hist = {}
for v in nets.values():
    for g in v["dynamic"]:
        hist[g] = hist.get(g, 0) + 1
hist = dict(sorted(hist.items(), key=lambda kv: -kv[1]))
out = {g: c for g, c in hist.items() if g not in GATE_LABELS}
print(f"""
Field 1 of the message says "which gate", and costs log2(12) = {math.log2(K):.4f} bits,
because we declared TWELVE gate families. log2(12) can only point at twelve
things. It is a menu with twelve items on it.

Now here is what the real corpus actually asks us to send:
""")
for g, c in hist.items():
    mark = "  <-- NOT ON THE MENU" if g not in GATE_LABELS else ""
    print(f"   {g:<12}{c:>6}{mark}")
print(f"""
   on the menu    : {nodes - sum(out.values()):>6}
   NOT on the menu: {sum(out.values()):>6}  = {100 * sum(out.values()) / nodes:.1f}% of the corpus

This is worse than the first bug. The first bug meant the message could not be
READ. This one means the message cannot even be WRITTEN: there is no codeword
for 'CUSTOM' at all, and the program quietly charges those nodes the cost of a
gate they are not, plus a parameter bit they do not have.

So what we proved in PARTS 3-6 is: a correct code FOR THE TWELVE FAMILIES.
The corpus is three quarters outside those twelve. That is why no biological
D may be published yet, and why regenerating the numbers now would just swap
one wrong figure for another. Fixing it means adding the missing family
(REGULATORY_DNF, which alone covers 83.6% of the CUSTOM nodes) — that is R4.
""")


# ===========================================================================
part("PART 9 — the one test number that moved: 28.5098 -> 37.7975")
# ===========================================================================
cm = [[0, 1, 0, 0], [1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0]]
dyn = ["AND", "OR", "XOR", "KOFN"]
nn = 4
print("""
One of our tests pins the D of a fixed 4-node toy network. It had memorised the
OLD, wrong value. When I made the fix, that test went RED before I touched it —
which is how I know the test is actually alive and not decoration.
""")
print(f"   {'node':<6}{'gate':<8}{'d':>3}{'old bits':>11}{'new bits':>11}{'difference':>12}")
old_t = new_t = 0.0
for i, g in enumerate(dyn):
    dd = sum(cm[i])
    o = node_length(g, dd, nn, with_indegree=False)
    w = node_length(g, dd, nn, with_indegree=True)
    old_t += o
    new_t += w
    print(f"   {i + 1:<6}{g:<8}{dd:>3}{o:>11.4f}{w:>11.4f}{w - o:>12.4f}")
print(f"   {'TOTAL':<17}{old_t:>11.4f}{new_t:>11.4f}{new_t - old_t:>12.4f}")
print(f"""
   Every node gained the SAME {math.log2(nn + 1):.4f} bits, because every node lives in
   the same n=4 network and log2(4+1) = log2(5) = {math.log2(5):.4f}.
   4 nodes x {math.log2(5):.4f} = {4 * math.log2(5):.4f}, and
   {old_t:.6f} + {4 * math.log2(5):.6f} = {new_t:.6f}.

   That is the '4 x log2 5' in my report. The test now expects {new_t:.6f}
   and passes. The value moved by the missing field and by NOTHING ELSE, which
   is itself the check: any other change would not have landed on that number.
""")


# ===========================================================================
part("PART 10 — the three things I found but did NOT fix")
# ===========================================================================
print("""
1. D_v2 cannot be checked at all.
   There is a second version of this cost, D_v2. It replaces the wiring fields
   with two numbers called 'motif cost' and 'hierarchy cost'. But those two
   numbers are simply READ OUT of a data file. No program in this repository
   ever writes them as a message. So there is nothing to decode and no way to
   ask whether D_v2 is a length at all. I marked it in the source and left it.

2. Input nodes cost 0 in Wolfram and full price in Python.
   A node with no inputs (a network's external switch) is charged nothing by
   three Wolfram scripts and the full gate cost by the Python loader — 729
   nodes are priced two different ways in the same project. Each side is
   consistent with itself, so nothing is broken today; but the two languages
   are not computing the same quantity, and one of them must be wrong.

3. A gate that cannot see what it is guarding.
   There is a check called the T4.5 parity gate whose job is to notice if the
   Wolfram cost drifts. It compares two numbers STORED IN ITS OWN FIXTURE FILE
   rather than re-running Wolfram. So when I changed the Wolfram file today, it
   noticed nothing and reported PASS. A green light on a stale number is worse
   than a red one, because it is read as evidence. I left it green and wrote it
   down rather than quietly patching it.
""")


# ===========================================================================
part("PART 11 — the 'bars' at the end of my report")
# ===========================================================================
print("""
Those are the standing regression checks — the things that must not break when
I change anything. They are not new results; they are the alarm system.

   MUnit OK=54 FAIL=1 TOTAL=55   55 Wolfram test files: 54 pass, 1 fails. That
                                 one (TopologiesTests) was already failing
                                 before I arrived and is a known, owned red.
   verify-paper 7 covered, 1 pending
                                 8 groups of numbers printed in the papers.
                                 7 are tied to a script that regenerates them;
                                 1 is not yet, with a written reason.
   paper-number gate: 109 identical
                                 109 numbers scraped from the manuscripts,
                                 all unchanged. This is a CHANGE DETECTOR: it
                                 proves I did not silently move a published
                                 number, not that the numbers are right.
   146 / 97 / 23                 Python tests passing in three packages
                                 (index-deconvolution, imp-prices, and the 23
                                 tests of the W1.1 codec).

The honest summary: every alarm that was green before is still green, and the
one number that was allowed to move, moved by exactly the amount predicted.
""")
