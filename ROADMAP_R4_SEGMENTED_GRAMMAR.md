# ROADMAP — Route 4: Segmented Gate-Grammar Code (persistent TODO)

**Status:** DESIGN AGREED — AWAITING WAVES 3–4 COMPLETION. Do not execute
before then. **Retake point:** draft the full pre-registration (segmenter
spec, frozen catalogue, controls, thresholds) and HALT for author sign-off
before any run, D-7 discipline. **Registered:** 2026-08-24, author directive
plus post-gate design discussion; superseded by nothing.

## Origin

Author proposal: BDM conquers large objects by divide-and-conquer over small
windows scored against an empirically enumerated CTM table; the index-set
method can run the same divide-and-conquer with *exact* per-window mechanisms
(decimal anchor + sumandos) and *analytic* code lengths. This continues the
method's founding intuition — nested patterns, patterns of patterns, holistic
view first, then short rules that replicate behaviour exactly (OEIS thread
noted as future context). It also serves the finance programme directly
(Payoff below).

## Concept mapping (BDM <-> index-set analogue)

| layer | BDM | Route 4 |
|---|---|---|
| base layer | empirical CTM table (TM enumeration <= ~12 bits) | analytic closed-form index-set codes (no table, no arity ceiling) |
| decomposition | object -> <=4x4 windows | string -> segments per declared policy |
| per-window value | CTM lookup (approximate) | exact minimal mechanism: support + named gate + anchor/sumandos code |
| repetition penalty | Shannon-style log2 multiplicity | mechanism dictionary: transmit once + occurrence list |
| overlap handling | approximate punishments | exact boundary accounting (compositional mechanisms; shared inputs counted once) |
| failure mode | returns a number regardless | refuses: proof of inconsistency, LUT fallback priced honestly |

Label discipline: outputs are **"codelength under declared grammar G"** and
**"recovered mechanism under declared frame F"** — never bare "algorithmic
complexity".

## Kolmogorov framing

For fixed G, L_G(x) is a computable upper bound on the shortest program in G
reproducing x; K(x) <= L_G(x) + O(interpreter + G-choice). BDM is likewise an
upper-bound family built on an empirical table. Neither touches true K; on
mechanistic objects expect L_G much smaller than BDM; on random objects both
must converge to entropy-like values — that convergence is the *negative
control passing* and is uninformative as validation. Discriminative claims
live only on mechanistic objects.

## Frozen decisions (author-accepted 2026-08-24)

- **D1 segmentation:** refine-on-residual — fit ONE global mechanism first;
  recurse locally only where residuals force it; refinement granularity fixed
  ex ante. Near-right rule frozen: keep the global mechanism iff its residual
  costs less than local replacement would.
- **D2 repetition:** mechanism dictionary — each distinct mechanism transmitted
  once, deterministic occurrence list, pointer cost paid (~log2 #segments).
  Exact-match on full mechanism tuple only (no fuzzy matching, v1).
- **D3 frame:** per-segment inferred minimal support, hard cap d = 3;
  candidate input set fixed at registration; the CAP is frozen, never the
  answer.
- **D4 scope:** v1 = 1-D binary strings only (synthetic concat/regime-switch
  controls + WTI daily binarised natural case). Panels/grids deferred.
- Family catalogue (twelve families + LUT tail) frozen at registration;
  catalogue growth only via dated amendment, catalogue cost paid in code.
- Cut points are knobs: either declared or charged in the code (MDL-correct);
  never free search.
- Prefix-free end-to-end: per-component Kraft checks exist in the suite; the
  join protocol gets its own test before any length is quoted.
- All recovery/equality claims elementwise (U8).

MDL note (author question, settled): MDL is not Shannon — it is the principle
"best model = shortest total code", agnostic to coding language. Our grammar
codes ARE the MDL instantiation; Shannon formulas enter only in explicit
probability terms (residuals). Using BDM as the length function would be
circular inside any comparison against BDM and is not self-delimiting without
work; BDM is quoted only as a rival measure's output.

## Standing controls (all pre-declared)

1. rule-110 positive (single law, whole string),
2. uniform-random negative (no false structure expected),
3. regime-switching positive (e.g., 110||30||110||45 with known cut points;
   segmentation must recover them elementwise),
4. natural-series case (WTI daily binarised): expected LUT dominance/refusal
   per Gate 1.0; pre-register the threshold for the "short lawful pockets"
   hypothesis — motivating shape: the March-2020 seven-pivot window.

Agreement-with-Shannon on noise = negative control passing; uninformative as
validation.

## Routes (restated for the record)

- R1 exp04 gains a Zenil arm — head-to-head on literature .bnet ground truth.
- R2 common-encoding bit-commensurability protocol — DEFERRED (C30 risk;
  defensive appendix only; NULLS.md nuisance rule applies if ever run).
- R3 E. coli declared-semantics synthesis (rules written from RegulonDB signed
  graph under documented convention) — round-trip + head-to-head become
  defined; permanently labelled synthetic-model benchmark, never biology
  recovery.
- R4 this instrument — RECOMMENDED LEAD, folding R1 and R3 in as application
  arms; R2 stays out unless forced.

Recommendation on record: execute R4's pre-registration after Waves 3–4, with
R1+R3 folded in; R2 deferred.

## Finance payoff

A per-segment law-density profile along a series timeline is a new instrument
for imp-prices: Gate 1.0 established panel-wide absence of deterministic
structure (0/14 nodes); segmented analysis asks the finer question — do short
mechanistic stretches exist? Falsifiable, pre-registerable, and rendered
honestly (the profile itself is the G1 object).

## Verified supporting facts (pointers)

- BDM small-scale blindness: FINDINGS C22 (3.2 sigma at 4x4, "unusable").
- Named-family coverage 17/256 arity-3 (6.6%): FINDINGS C21; LUT fallback
  covers the rest; catalogue growth mechanically easy but semantically
  diluting if total.
- Panel stochasticity: C20 (0 of 14 nodes named), Gate 1.0 base rate.
- String precedent: Fig. 1 mirror inferred b[i] = NOT b[i-1] and ran it
  forward (imp-causalNet-paper).
- Majority-vote robustness precedent: rule 110 recovered at 20% noise.
- Kraft checks already enforced per code component (bitacora 04 s1);
  residual_bits implemented (src index_set).
