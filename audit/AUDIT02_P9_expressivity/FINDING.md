# AUDIT02/P9 — the CA-arm "10/10 exact" criterion is satisfied by construction

**Status: FINDING, reported not remediated.** The artefact it concerns is
pre-registered (`imp-causal-paper/index_method_comparison/PROTOCOL.md`, D-7,
approved 2026-08-24). Protocol §5.4 forbids outcome-dependent changes, so
nothing here rewrites that result. The adjudication is the author's.

## Claim under audit

`imp-causal-paper/results/index_method_comparison/capability_table.md`:

> **CA summary: 10/10 rules exact** (0 mismatched cells total).

The hash manifest verifies (`VERIFY: PASS — 2 files match manifest`) and the
producer exists and is pre-registered. Integrity and provenance are sound. What
follows is not about either.

## The control

The 10 rules were frozen in advance, which is correct practice, but the
comparison was never run against the coordinate that makes the number
interpretable: **all 256 ECA rules**. `expressivity_control.py` runs the
identical pipeline — same `deconvolve_ca`, same `WIDTH=11`, `STEPS=30`,
`N_ICS=60`, `RADIUS=1`, same per-rule seed `SEED + rule`, same
`repertoire()`-based elementwise mismatch count — and changes only the rule list.

Positive control: the harness reproduces the committed **10/10** exactly, so it
is the same measurement, not a re-implementation.

Result:

```
exact global-map recovery : 256/256
the 10 chosen rules       :  10/10
```

**Every ECA rule is recovered exactly.** A criterion that no member of the
population can fail carries no information about the ten that were sampled.

## Mechanism

`deconvolve_ca` searches a gate space that includes two functionally complete
representations, both outside the canonical twelve
(`causalbool.EXTENSION_GATE_TYPES`, so outside the Wolfram parity proof):

| gate | why it cannot fail |
|---|---|
| `LUT` | an explicit truth table over the connected inputs — every 3-input Boolean function *is* such a table |
| `REGULATORY_DNF` | disjunction of activator/inhibitor clauses — DNF is functionally complete |

Over the exact set of 256, the families used are:

```
REGULATORY_DNF  178      LUT  24      REGULATORY  12 (6 + 6 mixed)
canonical-only   34
```

For the ten committed rules specifically, **8 of 10 use an extension gate**
(`REGULATORY_DNF` ×6, `LUT` ×2); only rules 254 (`OR`) and one `CANALISING` rule
are recovered inside the canonical twelve.

## Two consequences

**1. The number does not support the sentence it sits under.** The table is
headed "index method vs Zenil calculus (CA arm)". A reader takes 10/10 as
evidence about the index method's reach. It is instead a restatement of
functional completeness. The informative statistic is available and is
*already computed by the same run*: **canonical-only exact = 34/256**, and for
the ten chosen rules, 2/10.

**2. It contradicts the programme's own expressivity position.** R4 PROTOCOL
Addendum A3.1 pins frame expressivity at **46 of 256** via the mirror-tested
catalogue, precisely so that unreachable rules cannot be claimed. Rule 110 is
unreachable under that pinning (audit finding F1). The CA arm reports rule 110
recovered exactly, via `REGULATORY_DNF`. Both statements are true in their own
frames; they cannot both be quoted as "the index method recovers X" without
saying which gate set is in play.

Reconciliation of the two counts, for the record — they nest, so this is a
confirmation, not a second defect:

```
canonical-only exact here      34
R4 catalogue distinct tables   48  (46 non-constant, matching A3.1 exactly)
34 ⊆ 48 ✓        48 \ 34 = {0,10,12,34,48,68,80,175,187,207,221,243,245,255}
```

The 14-rule gap is the greedy deconvolver declining to search the canonical
families exhaustively before falling back to `LUT`/`REGULATORY_DNF` — a search
limitation, not a semantic disagreement.

## A separate, smaller point: criterion substitution

PROTOCOL §5.1 pre-registered exact recovery as *"recovered connectivity C'
equals C elementwise AND recovered gates D' equal D gate-for-gate"*, and §4 as
*"the engine either reproduces the generating (C, D) elementwise or it does
not"*. An ECA rule has no ground-truth named gate `D`, so that criterion is
inapplicable to the CA arm. What was delivered is **global-map equality**, a
behavioural criterion. That substitution is defensible — arguably it is the only
gradable criterion available — but §5.4 makes it a protocol deviation, and it
is recorded nowhere.

## Recommended adjudication (author's call)

1. Report **both** numbers in the capability table: global-map equality
   (10/10, with the note that 256/256 is attainable) and canonical-only
   recovery (2/10, 34/256). Neither is wrong; only the first alone is
   misleading.
2. Log the §5.1 → global-map criterion substitution as a dated deviation.
3. Decide whether the CA arm should score *ours* at all under §5.2, given that
   the criterion it passes is not discriminative.

Nothing above impugns the data, the seeds, the manifest, or the pre-registration
discipline, all of which are in order.

## What is clean, checked in the same pass

- `index-deconvolution` exp02 **200/200** exact repertoire — gate pool is
  `"all"`, which is the canonical twelve *without* `LUT`/`REGULATORY_DNF`. A
  genuine closed-loop generate-and-recover test, and it honestly reports
  96.12% for connectivity and gate-function recovery rather than rounding to
  100%. Not affected.
- `imp-causalNet-paper` `causal_models._name_gate` falls back to the string
  `"LUT"` only as a *cosmetic name* when `identify_gate` cannot name a table
  the search already found; the model must still be consistent with every
  sample, and the `success=False` branch is reachable. Not vacuous.
- `imp-pathinfo-paper/src/imp_pathinfo/causalbool_mirror.py` imports the root
  `causalbool` rather than copying gate semantics — no third divergent engine.
  It passes `MAJORITY` empty params, so it rides the default, which is proven
  unchanged below.
- `imp-prices/vendor/causalbool.py` and `index-deconvolution/src/causalbool.py`
  are byte-identical (`4385c08b62fd12f8b8f5fba1117a2ead`) — the two-copies rule
  survived the Phase-1 edits.
- AUDIT02/P2 default semantics are unchanged, verified exhaustively rather than
  argued: `MAJORITY` over 8,190 vectors (arity 1–12) and `KOFN` over 106,494
  (vector, k) pairs, **0 mismatches** against the pre-Phase-1 expressions, with
  a planted-defect control (`tiePolicy="atOrAbove"` → 1,274 mismatches) proving
  the check can fail.
- `imp-prices/experiments/c36_window_distribution.py:123` patches
  `validate_prices` — inspected, and it is a labelled, documented guard bypass
  used to reproduce pre-guard behaviour for provenance, with the guarded path
  computed alongside for comparison. Legitimate forensics.

## Reproduce

```bash
venv/bin/python audit/AUDIT02_P9_expressivity/expressivity_control.py
```
