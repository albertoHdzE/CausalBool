# search-diagnosis-v1-r1 — decision memo

Recommendation: **`BOTH_SEPARATELY`** — two separate, independently reviewed
continuations: a boundary-search change for the boundary families and a representation
change for the period-type families. Never one combined source version.

This is a post-hoc recommendation on already inspected data. It is not a superiority
claim, not a confirmation and does not by itself authorize an algorithm. Machine record:
`DECISION.json` (gates, rule, flags, basis lines generated from `analysis/flags.json`).

## Evidence gates

All 416 + 176 + 576 jobs completed `ok`; B0 reproduced the saved stage-B telemetry in
208/208 strings with 0 deterministic mismatches; 176/176 supplied references reproduced;
0 of 1,152 H − C identity failures; D1 found 0 problems across 1,792 cases and 28,672 rows
and reproduced the accepted primary estimate exactly. Neither `INVALID` nor
`INCOMPLETE` applies.

## Rule

Stated in `DECISION.json` → `rule` and written after the measurements (post-hoc). A
search signal requires that, in the boundary-family strings where the full arm loses to
the portfolio, a same-language supplied-cut partition beat the saved full archive in a
majority while B8 changed only a small minority. A representation signal requires that,
among D4 strings where the translated method won the portfolio and HID loses, H = T in a
majority. Both in disjoint family groups gives `BOTH_SEPARATELY`.

## Why, cell by cell

**Search (F12 at ≥ 4,096 bits, S02 at 65,536).** The losing strings are concentrated
here: confirmation F12 4,096 (40 of 40 strings), transfer F12 at all three sizes (8 of 8
each) and S02 (2 of 16 at 4,096, 6 of 16 at 65,536). Budget is not the limitation: B8
changed one of 176 targets (40 bits) and none of 32 controls; every B8 job ended by
`no_strict_improvement`. Yet in all 72 losing strings a supplied-cut partition in the
unchanged leaf language beats both the saved full archive and the portfolio, and the
cheapest strictly reachable partition beats the portfolio in 32 of 40 confirmation F12
4,096 strings, 6, 2 and 4 of 8 at transfer 16,384, 65,536 and 131,072, and 14 and 16 of
16 in the S02 cells (§3 of `REPORT.md`). Restricted path barriers exist in 22 strings,
all positive-cost steps, concentrated at transfer F12 65,536 (6 of 8) and 131,072 (4 of
8). Of the useful supplied cuts, about half (129 of 252) have a B0 cut within 8 bits and
the rest have none. The dominant obstacle in this restricted space is which cut
positions B proposes; the strict-improvement rule is secondary, and caps are
negligible.

**Representation (F01, F02, F03, F05).** Of 386 strings whose portfolio winner was the
translated period or pair-grammar archive, HID loses on 367, and on 282 of those the
saved full archive has exactly the translated length (H = T). There, no search change
inside the frozen language can recover the loss to that baseline: the search already
reaches the proposal and pays its HID cost. No translation was shorter than H (0/1,152),
so D4 found no missed baseline structure. The penalty is structural: an exact repeat
costs 40–48 bits more than the period codec, a ragged repeat 96–352, and each pair rule
pays an extra opcode and arity field; its per-bit size shrinks with n, which is why it
weighs most in the 256- and 1,024-bit cells that the accepted primary estimate weights
equally.

**Why not one scope.** The two mechanisms live in disjoint family groups (boundary
families versus period-type families) and touch different owners
(`hierarchy/segmentation.py` versus `hierarchy/model.py`/`wire.py`/`decode.py`).
Choosing one would leave the other group's losses unexplained, and combining them in
one source version would make neither effect attributable.

**Priority, offered for the supervisor's choice.** The search continuation is the only
one of the two where the measured space shows the sign of the loss can reverse (supplied
partitions shorter than the portfolio). The representation continuation can only reduce
the deficit: the exact-repeat floor of 40–48 bits above the period codec remains under
any HID-v1-style DAG. I would run the search study first.

## What would falsify the proposed explanations

* Search: an input-only change that makes B propose cuts near the useful supplied
  positions (measured by the same within-8-bits location statistic on development
  strings) does not shorten the full archive in the F12 4,096 cell, or shortens it only
  where the new cuts coincide with no supplied position. Then the cause is the leaf
  heuristic or the language, not cut proposal.
* Representation: a change that removes the tail literal and the CONCAT from ragged
  periodic translations does not reduce H by the bytes predicted from the saved ledgers
  in the H = T strings (an exact, deterministic prediction), or reduces it while the
  primary-cell deficits stay unchanged in sign and size.

## What remains unidentified

Why B stops (imprecise accepted cuts, unproposed cuts, or the shortest-period leaf
heuristic) is not separated by these data. The 85 losses with H < T are not decomposed.
F06–F11 are outside D2–D4, and F08, F09 and F11 carry the largest per-bit losses in the
whole run. A missing improvement here is not a language-impossibility statement; D3 is
truth-assisted and restricted to at most five supplied cuts; D4 is proposal-specific.

A concrete draft for each continuation is in `NEXT_PROTOCOL_DRAFT.md`; no seeds were
generated and no source version was implemented.
