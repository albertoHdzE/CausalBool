# PROTOCOL — Route 4: Segmented gate-grammar codelengths for 1-D binary strings

**Status: FROZEN 2026-08-25 — signed off by the author (directive "proceed as
recommended", adopting route (b): approval conditional on Addendum A1 below).
No result-dependent changes permitted; deviations only as dated addenda below,
logged BEFORE adoption, with any affected run discarded and superseded (T4.3
precedent).**

Drafted 2026-08-25 by the boarding agent from the roadmap's frozen decisions
(D1–D4, author-accepted 2026-08-24) and its standing controls. Every parameter
below is fixed ex ante; none has been tuned against any R4 result (no R4 result
exists).

## 1. Object and labels

Input object: one finite binary string b[1..n]. Output objects, always labelled:

- **L_G(x)** — "codelength of x under declared grammar G" (bits).
- **M_F(x)** — "recovered mechanism under declared frame F" (segmentation +
  per-segment mechanism tuples), or **REFUSED** with reasons.

Never bare "algorithmic complexity". Framing (roadmap, binding): for fixed G,
L_G is a computable upper bound on the shortest program in G reproducing x;
K(x) <= L_G(x) + O(interpreter + G-choice). Neither G nor BDM touches true K.
On mechanistic objects expect L_G << BDM; on random objects convergence to
entropy-like values is the NEGATIVE CONTROL PASSING and is uninformative as
validation. Discriminative claims live only on mechanistic objects.

## 2. Scope (frozen decision D4)

v1 = 1-D binary strings ONLY: synthetic controls (§6 C1–C3) + WTI daily
binarised natural case (§6 C4). Panels/grids deferred. R1/R3 fold in later as
application arms under the successor plan; R2 stays out unless forced.

## 3. Frame F (frozen)

| Component | Frozen value |
|---|---|
| Mechanism catalogue | The TWELVE families (AND, OR, XOR, NAND, NOR, XNOR, NOT, IMPLIES, NIMPLIES, MAJORITY, KOFN, CANALISING) + LUT tail. Catalogue ID `R4-CAT-v1`; growth only via dated amendment, catalogue identity transmitted in the code (version header), catalogue cost paid inside L_G. |
| Candidate inputs | Lagged values {b[t−1], b[t−2], b[t−3]} only. |
| Support cap | Hard d = 3 (D3). The CAP is frozen, never the answer: hitting it is reported, not relaxed. |
| Per-segment support | Minimal support inferred within the candidate set (smallest subset achieving the fit; ties → lexicographically smallest subset). |
| Ordering conventions | LSB-canonical internal representation; interop via Φ-exactly-once (`GOVERNANCE/ORDERING.md`). Gate-parameter coordinate conventions per ORDERING.md §4b (pair/i absolute vs canalisingIndex Ic-relative — pinned by executed witnesses). |
| Tie policies | MAJORITY tiePolicy default ties→0 (plan D-3). KOFN params frozen to 1 ≤ k ≤ n ≤ 3. NOT is arity-1. Constant segments (all-0/all-1) are NOT catalogue mechanisms; they ride the LUT tail, priced honestly. |
| ECA-rule encoding (for controls) | Radius-1 ECA rule r ↔ 3-lag recurrence: neighbourhood (b[t−3], b[t−2], b[t−1]) maps to rule bit via Wolfram convention value = 4·b[t−3] + 2·b[t−2] + 1·b[t−1]; output bit = ⌊r / 2^value⌋ mod 2. Generation starts at t=4 from three rng-seeded initial bits; recovery is judged on positions 4..n only, and this exclusion is stated wherever results are quoted. |

Exact-match on FULL mechanism tuples only (family + params + support) — no
fuzzy matching, v1 (D2).

## 4. Grammar G and codelength accounting (all components Kraft-checked)

L_G(x) is the sum of transmitted components; EVERY component carries a Kraft /
prefix-free check (suite-enforced), and the JOIN protocol gets its own test that
must be green BEFORE any length is quoted anywhere (AC-R4-1).

1. Header: n, segment count S, catalogue ID, binarisation/granularity knobs actually used.
2. Mechanism dictionary (D2): each DISTINCT mechanism tuple transmitted once,
   in order of first occurrence; dictionary size |D| coded self-delimitingly.
3. Occurrence list: segments in ascending positional order; per segment its
   dictionary index (ceil(log2 max(|D|,2)) bits) + length (self-delimiting).
4. Cut positions: k interior cuts, each ceil(log2 n) bits (knobs charged, never
   free search).
5. Residuals: per segment either 0 (exact mechanism) or the honest fallback:
   raw copy of the segment (length · 1 bit) flagged `LUT-fallback`. A fallback
   is NEVER reported as a recovered mechanism.
6. Pointer overhead is explicit: the "~log2 #segments" repetition penalty is
   realised as component 3; nothing else is free.

Refusal semantics: the instrument returns REFUSED (with the blocking proof /
inconsistency reason) rather than a number it cannot stand behind; refusals are
first-class outputs and are counted per control.

## 5. Segmenter spec (frozen decision D1: refine-on-residual)

Deterministic; contains NO randomness. Seeds exist only in data generation.

```
SEGMENT(s):
  1. fit = argmin over catalogue of [mechCode(mech, s) + residCode(mech, s)];
       ties → lexicographically smallest (family, params, support) tuple.
  2. R = {positions i in s where mech prediction != actual}.
  3. if R empty: return single-mechanism segment (exact).
  4. candidate cuts: boundaries of maximal runs of R, snapped OUTWARD to the
     nearest multiple of b (granularity b = 8, fixed ex ante); drop cuts that
     would create segments shorter than b.
  5. accept the split iff total L_G(strict) decreases WITH cut costs charged;
       else keep the global mechanism (this IS the frozen near-right rule:
       keep global iff its residual costs less than local replacement).
  6. recurse SEGMENT on each child.
```

Termination: integer codes, monotone non-increasing bounded below ⇒ finite.
The near-right acceptance rule makes "almost-right global law beats fragmented
local patches" an enforced outcome, not a hope.

## 6. Standing controls and success criteria (all pre-declared, binary)

Common settings: 20 seeds per cell; generation rng = `random.Random(f"{tag}:{cell}:{seed}")`
(T4.3 D1 lesson: Python needs str/int seeds); every recovery/equality claim is
ELEMENTWISE with the symmetric difference and its location reported (U8) —
never counts alone; determinism AC: any rerun of a committed generator is
byte-identical.

- **C1 rule-110 positive (single law, whole string).** n ∈ {256, 1024} × 20
  seeds. PASS ⟺ 40/40 runs yield M_F = one segment whose tuple is exactly the
  rule-110 recurrence of §3, zero residual on positions 4..n (symDiff ∅).
- **C2 uniform-random negative.** iid fair bits, n ∈ {128, 512, 2048} × 20
  seeds. PASS ⟺ per cell mean(L_G/n) ≥ 0.90 (one-sided: FALSE STRUCTURE can
  only shorten; upper-side overhead is reported, not gated) AND the TOTAL
  number of non-LUT dictionary mechanisms transmitted across all 60 strings is
  ≤ 2 (declared chance budget), with every occurrence listed elementwise
  (string, position span, tuple) if any occur. Agreement-with-Shannon here =
  negative control passing; uninformative as validation.
- **C3 regime-switching positive (segmentation must recover cuts ELEMENTWISE).**
  RS-A = rules [110, 30, 110, 45], blocks of 64 (n=256); RS-B = [30, 110]
  alternated ×5, blocks of 32 (n=320); 20 seeds each; block boundaries are the
  declared cut set. PASS ⟺ 20/20 per regime with (i) recovered cut set ==
  declared cut set (symDiff ∅) and (ii) per-segment tuple == generating rule's
  tuple, zero residuals.
- **C4 natural case: WTI daily binarised.** Series: imp-prices pinned WTI
  artifact (file + date range recorded in the results commit; never fetched
  live). Binarisation declared NOW: b[t] = 1 iff daily close-to-close log-return
  > 0, else 0. Expectation per Gate 1.0 (panel stochasticity, C20): LUT
  dominance / refusal. Pre-registered "short lawful pockets" hypothesis
  (motivating shape: March-2020 seven-pivot window): a POCKET is a maximal
  contiguous window of length ≥ 16 on which exactly ONE catalogue mechanism
  reproduces the window EXACTLY (zero residual, elementwise), support ≤ 3,
  verified by regenerating the window from its three pre-window symbols
  (windows without three available predecessors are excluded and counted).
  Reporting: the per-segment law-density profile along the timeline IS the
  G1 render (raw object); all examined windows are enumerated; found-pocket
  count is stated against C2's chance budget scaled by windows examined —
  descriptive, no p-value theatre. Any pocket claim additionally requires the
  C2-style elementwise listing.

## 7. Implementation-phase acceptance criteria (successor plan; binary)

- **AC-R4-1** Join/Kraft test green (every component Kraft sum ≤ 1; end-to-end
  join round-trips) BEFORE any L_G value is quoted in any document.
- **AC-R4-2** Determinism: committed generators and segmenter reproduce their
  artifacts byte-identically on rerun.
- **AC-R4-3** Every recovery/equality claim ships elementwise symmetric-
  difference evidence + location (U8); datasaurus gates run on every equality
  claim before it enters any document.
- **AC-R4-4** Refusal path demonstrated by a constructed test case: REFUSED
  with reason, honestly priced, never silently LUT'd into a "mechanism".
- **AC-R4-5** This protocol's commit precedes the earliest R4 results commit in
  git history (AC-2.4e pattern, git-checkable).
- **AC-R4-6** Figures render the raw objects (strings, segment maps, profile
  timeline) — a plot of a statistic is not a render of the object (G1/G1b).
- **AC-R4-7** No engine (WL core / packaged Integration`) modification; new
  instrument code lives where the successor plan places it; if
  `index-deconvolution/src/{causalbool,deconvolution}.py` are ever touched, the
  vendor two-copies rule applies same-commit; any hash-order-sensitive output
  records `PYTHONHASHSEED`.

## 8. Explicitly out of scope for v1

Panels/grids (2-D BDM analogue), R2 common-encoding commensurability, fuzzy
mechanism matching, catalogue growth, arity > 3 supports, streaming/online use,
noise-robustness claims (majority-vote 20% precedent noted as future context
only), any biological-recovery reading (R3 remains a declared-semantics
synthetic benchmark when folded in).

## 9. Sign-off

**RECORDED 2026-08-25:** author adopted the boarding agent's recommendation —
route (b): approve conditional on Addendum A1 (empirical surrogate-null claim
gate for C4) and A2 (derived C2 budget rationale). Freeze effective with the
commit carrying these addenda; approval provenance = session directive, quoted
in that commit message (AC-2.4e pattern: no R4 results commit may precede it).
Execution opens `SUCCESSOR_PLAN_R4.md`; nothing runs under AUDIT_FIXING_PLAN_01
authority.

## Addendum A1 (2026-08-25, pre-results) — C4 pocket CLAIMS gated on an empirical surrogate null

Detection keeps w_min = 16. A **claim** about real-data pockets additionally
requires all of:

1. **Surrogate null:** ≥ 100 iid fair-coin binary surrogates of length matched
   to the binarised WTI series are run through the IDENTICAL pipeline and
   pocket definition. Destroyed dimension: all deterministic structure.
   Held fixed: length, alphabet, pipeline, thresholds. Declared limitation:
   iid fair coins are the null; volatility-clustering structure in returns is
   part of what is being tested against, not matched.
2. **Claim gate:** observed pocket count exceeds the 99th percentile of the
   surrogate per-series pocket counts AND observed maximum pocket length
   exceeds the surrogate maximum. Otherwise the honest verdict is "consistent
   with the exact-reproduction noise envelope" — which Addendum-derived
   arithmetic puts at ≈3×10⁻³ per window start at w=16 (≈24 raw hits expected
   on ~7000 observations; committed derivation:
   `experiments/r4_segmented_grammar/calibration.py`, MC-confirmed).
3. **Elementwise listing (unchanged, U8):** every claimed pocket listed with
   span + regenerating tuple + regeneration check.

Rationale: exact reproduction under exhaustive search is a multiple-comparisons
magnet; only a richest-control null licenses a positive claim.

## Addendum A2 (2026-08-25, pre-results) — C2 noise budget retained ≤2, rationale upgraded from assertion to derivation

The budget stands: ≤ 2 transmitted non-LUT dictionary entries across all 60
noise strings. Derivation: an isolated chance exact-reproduction fails the
segmenter's strict-improvement acceptance because its bit savings are smaller
than its charged overhead (mechanism code + dictionary share + pointer + cut
costs); pattern-luck alone therefore does not transmit mechanisms. The budget
guards aggregate/residual risk across seeds and cells. Backstop: ANY transmitted
noise mechanism with span ≥ 16 is reported individually regardless of total
count. The pre-economics envelope (raw hits before economics) is recorded by
the committed calibration tool for transparency; it is NOT the expected
transmission count.

## Addendum A3 (2026-08-25, pre-results; adversarial-review remediation) —
controls re-designated to reachable rules, expressivity pinned by mirror test,
C2 tightened, A1 null upgraded

Adopted following an independent adversarial review (F1–F5) whose substance was
reproduced by the boarding agent before adoption. No R4 result exists; every
change below is therefore pre-registration hygiene, not tuning. This addendum
SUPERSEDES the following clauses, which remain in place above unmodified:
§6 C1 (rule-110 criterion), §6 C3 (rules 110/30/45), §4.5 sentence "Kraft gives
…" is unaffected, §6 C2 threshold 0.90, Addendum A1 item 1 (iid-fair-coin-only
null) and A1 item 2's quoted envelope arithmetic.

**A3.1 Frame expressivity (authoritative).** The mechanism catalogue is the
ApplyGate-generated, mirror-tested export
(`catalogue_from_gates.json`; generator `tools/r4_catalogue_from_gates.wl`;
elementwise parity `tools/r4_catalogue_mirror_test.py`, exit-gated). Usable
(non-constant) mechanisms: 177; distinct truth tables: 46; **reachable 3-input
rules: 46 of 256**. Supports are ALL non-empty subsets of {b[t−1], b[t−2],
b[t−3]} including non-contiguous ones ({1,3} admissible); KOFN carries both
strict modes as distinct mechanisms; constants ride the LUT tail and are
excluded from the catalogue. Controls may only nominate rules from the
exported reachable set.

**A3.2 C1 (positive control) re-designated.** Rule **150** (= XOR₃ on lags
{1,2,3}) replaces rule 110: n ∈ {256, 1024} × 20 seeds each; PASS ⟺ 40/40
runs yield M_F = one segment whose tuple is exactly the rule-150 recurrence,
zero residual on positions 4..n (symDiff ∅).

**A3.3 C3 (regime-switching) re-designated.** RS-A = rules [150, 232, 150,
105] in blocks of 64 (n=256); RS-B = [90, 150] alternated ×5 in blocks of 32
(n=320) — RS-B exercises non-contiguous support inference ({1,3}). Cut set and
per-segment tuple criteria unchanged (symDiff ∅, 20/20 per regime).

**A3.4 C2 threshold tightened 0.90 → 1.00.** PASS requires per-cell mean
L_G/n ≥ 1.00: any honest grammar on iid fair bits carries non-negative
overhead, so mean < 1 now fires on genuine claimed compression rather than
essentially only on Kraft violations.

**A3.5 A1 null upgraded (two tiers, claim gate = BOTH).**
Tier 1 — marginal-matched surrogates: ≥100 Bernoulli(p̂) strings, p̂ = empirical
P(b=1) of the binarised series recorded in the results artifact.
Tier 2 — dependence-preserving surrogates: ≥100 circular-block shuffles of the
binarised series (block = 20 trading days), preserving short-range volatility
clock while destroying law structure. A pocket claim requires observed count >
99th percentile of surrogate counts AND max length > surrogate max under BOTH
tiers (house doctrine: marginal preservation, TRANSFERENCE.md; exp19/20
precedent).

**A3.6 Envelope figures superseded.** All previously quoted noise-envelope
numbers (including ≈3×10⁻³ per start at w=16 inside Addendum A1) derived from
the pre-fix catalogue/event mismatch and are RETIRED. Authoritative figures
(`calibration.py` v2, byte-identical rerun): P(any-start regeneration) =
1.67×10⁻⁴ ± 2.9×10⁻⁵ at w=16 → E[raw hits] ≈ 1.2 on ~7000 observations;
w=14: 9.6×10⁻⁴; w=12: 4.1×10⁻³; w≥20 below MC resolution (bounds 4.4×10⁻⁵,
2.7×10⁻⁶). Pre-economics label applies throughout.

## Deviations

- (none yet — section exists for dated addenda only)
