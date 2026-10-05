# search-diagnosis-v1-r1 — decision memo (corrected, reporting revision `report-r2`)

> **Corrected copy.** Computations: attempt `a1`, unchanged. This memo replaces the
> interpretation in the original `search-diagnosis-v1-r1/DECISION.md`, which is kept
> unchanged as a historical artifact. Corrections answer Codex review R1–R3
> (`supervision/search-diagnosis-v1-r1/REVIEW.md`); every number is read from
> `report-r2/outputs/` (`DECISION.json`, `flags.json`, `key_numbers.json`). The
> numerical comparison with a1's outputs is `report-r2/outputs/comparison_with_a1.json`.

Recommendation: **`BOTH_SEPARATELY`**, as an exploratory recommendation — two
separately reviewed continuations: a boundary-search change for the boundary families and
a representation change for the period-type families. It is not a proved decomposition of
the loss and not a reason to exclude future same-language search improvements on the
period-type families.

This is a post-hoc recommendation on already inspected data. It is not a superiority
claim, not a confirmation and does not by itself authorize an algorithm. Machine record:
`report-r2/outputs/DECISION.json` (gates, rule, flags, basis lines generated from
`report-r2/outputs/flags.json`).

## Evidence gates

All 416 + 176 + 576 jobs completed `ok`; B0 reproduced the saved stage-B telemetry in
208/208 strings with 0 deterministic mismatches; 176/176 supplied references reproduced;
0 of 1,152 H − C identity failures; D1 found 0 problems across 1,792 cases and 28,672 rows
and reproduced the accepted primary estimate exactly. Every intended record is available,
so neither `INVALID` nor `INCOMPLETE` applies. (The a1 reporting code could not have
produced either state on unavailable records — it raised `KeyError`; `report-r2` applies
the gates before any success-only quantity.)

## Rule

Stated in `DECISION.json` → `rule` and written after the measurements (post-hoc). A
search signal requires that, in the boundary-family strings where the full arm loses to
the portfolio, a same-language supplied-cut partition beat the saved full archive in a
majority while B8 changed only a small minority. A representation signal requires that,
among D4 strings where the translated method won the portfolio and HID loses, H = T **in
length** in a majority. Both in disjoint family groups gives `BOTH_SEPARATELY`.

## Why, cell by cell

**Search (F12 at ≥ 4,096 bits, S02 at 65,536).** The losing strings are concentrated
here: confirmation F12 4,096 (40 of 40 strings), transfer F12 at all three sizes (8 of 8
each) and S02 (2 of 16 at 4,096, 6 of 16 at 65,536). The specific B0→B8 cap increase
changed the output of one of 176 targets (40 bits) and none of 32 controls; every B8 job
ended by `no_strict_improvement`. This concerns that one increase on these strings; it
does not exclude resource limits under other searches. In all 72 losing strings a supplied-cut partition in the
unchanged leaf language beats both the saved full archive and the portfolio, and the
cheapest strictly reachable partition beats the portfolio in 32 of 40 confirmation F12
4,096 strings, 6, 2 and 4 of 8 at transfer 16,384, 65,536 and 131,072, and 14 and 16 of
16 in the S02 cells (§3 of `REPORT.md`). Restricted path barriers exist in 22 strings,
all positive-cost steps, concentrated at transfer F12 65,536 (6 of 8) and 131,072 (4 of
8). Descriptively, of the 252 supplied cuts in the 68 cheapest strictly reachable
subsets that beat H, 129 lie within 8 bits of a cut in the archive B0 **returned** and 123
do not. Returned cuts are not the cuts B proposed or evaluated: a cut could have been
proposed and rejected on an earlier partition. These data therefore do not rank cut
proposal, the accepted path, refinement and leaf construction as causes, and strict
reachability along some supplied-cut path does not show that B's automatic greedy path
could reach that state.

**Representation (F01, F02, F03, F05).** Of 386 strings whose portfolio winner was the
translated period or pair-grammar archive, HID loses on 367. On 282 of those the saved
full archive has the same **length** as the translation (H = T); on 261 the bytes are
identical and on 21 they differ (for example `confirmation-F01-1024-3003-ragged`,
period), so equal length is not the same proposal. Wherever H = T, H − C = T − C exactly:
the loss to that baseline equals this translation's measured penalty. That arithmetic
does not show that no search change inside the frozen language could recover the loss —
D4 prices only the translated proposal (protocol §§7–8), and even byte identity would not
prove optimality over all HID descriptions. No translation was shorter than H (0/1,152),
so D4 found no missed baseline structure. The measured, proposal-specific penalties: the
46 exact-repeat period translations cost 40–48 bits more than the period codec, the 350
repeat-plus-ragged-tail translations 96–352, and each pair rule pays an extra opcode and
arity field; the per-bit size shrinks with n, which is why it weighs most in the 256- and
1,024-bit cells that the accepted primary estimate weights equally.

**Why not one scope.** The two mechanisms live in disjoint family groups (boundary
families versus period-type families) and touch different owners
(`hierarchy/segmentation.py` versus `hierarchy/model.py`/`wire.py`/`decode.py`).
Choosing one would leave the other group's losses unaddressed. Separate contrasts are a
design preference for clean attribution; a combined version with controlled ablations
could also identify the two effects.

**Priority, offered for the supervisor's choice.** The search continuation is the one
where a measured (truth-assisted) space contains descriptions shorter than the portfolio:
supplied-cut partitions in the unchanged leaf language. For the representation side D4
measured no translation shorter than its baseline, but that is a property of these
translations, not a floor: whether some other HID description of those strings is
shorter was not measured. I would run the search study first; this is a preference, not
an inference from a bound.

## What would falsify the proposed explanations

* Search: an input-only change to cut proposal, whose proposed and evaluated cuts are
  logged directly (not inferred from returned cuts), that does not shorten the full
  archive in the F12 4,096 cell would count against the proposal hypothesis. It would not
  by itself place the cause in the leaf heuristic or the language: the accepted path,
  refinement, leaf construction and their interactions remain candidates.
* Representation: for a fully specified rewrite of the saved translations, the cost T′ of
  each rewritten proposal is exactly computable in advance (graph sharing and pruning,
  rule IDs, variable-length fields and the new wire envelope included); a measured T′
  that differs from it is a defect in the rewrite or its accounting. The full method's H′
  is not exactly predictable from H = T — the incumbent, proposals or search path can
  differ — so a disagreement in H′ is not automatically a codec defect. The explanation
  would be weakened if, on the period-type cells, the full method's measured reductions
  stayed far below the T − T′ reductions of the same strings' proposals.

## What remains unidentified

Why B stops (imprecise accepted cuts, unproposed cuts, or the shortest-period leaf
heuristic) is not separated by these data; returned cuts cannot separate them. The 85
losses with H < T are not decomposed. F06, F07 and F11 were sampled only as D2 controls
(at 4,096 and 65,536 bits); none was a D3 or D4 target, and F08–F10 appear only in D1.
F08, F09 and F11 carry the largest per-bit losses in the whole run, and no diagnostic here
targeted those losses. A missing improvement here is not a language-impossibility
statement; D3 is truth-assisted and restricted to at most five supplied cuts; D4 is
proposal-specific.

A concrete draft for each continuation is in `NEXT_PROTOCOL_DRAFT.md` (corrected copy
beside this file); neither is approved for implementation. No seeds were generated and
no source version was implemented.
