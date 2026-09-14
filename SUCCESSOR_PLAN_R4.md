# SUCCESSOR_PLAN_R4 — Segmented Gate-Grammar Execution (opened 2026-08-25)

**Status:** OPENED at R4 protocol freeze. Authority for everything
ROADMAP_R4_SEGMENTED_GRAMMAR.md now governs transfers here;
AUDIT_FIXING_PLAN_01 is CLOSED and holds no further jurisdiction.
**Binding inputs:** `experiments/r4_segmented_grammar/PROTOCOL.md` (FROZEN
2026-08-25 — its addenda are law), `GOVERNANCE/{ORDERING,NULLS,DESCRIPTION_LENGTHS,GLOSSARY}.md`,
MUnit BASELINE v2 (+ intended deltas, bracketed per U7).

Conventions: U1–U8 in force; one commit per task `[R4/<task-id>]`, push after
each; dated deviations to this file's log section (append-only); AUTHOR-DECISION
items halt their thread; datasaurus gates on every equality claim or quoted
number.

## Wave 0 — hygiene debt carried from close-out (engine-adjacent; bracket first)

| Task | Content | Notes |
|---|---|---|
| W0.1 ORDERING §7 migration | BioExperiments → LSB-canonical public contract per GOVERNANCE/ORDERING.md §7 | suite bracket before/after; mixed001 figures must stay invariant |
| W0.2 F36 exception coverage | Comparison.m / OnPossibleBehaviour.m keep ABSOLUTE canalising reading as documented exceptions — give them their own pinned tests or migrate to Ic-relative | ORDERING §4b authority; negative+positive controls |

Gate: both under fresh MUnit baseline bracket (record deltas); no paper-number
changes expected — if the gate moves, stop and log.

## Wave 1 — R4 instrument (per FROZEN protocol)

1. W1.1 Grammar/codec module + Kraft/prefix-free component checks (**AC-R4-1**:
   join test green before ANY length is quoted anywhere).
2. W1.2 Segmenter (D1 refine-on-residual, deterministic) + refusal path
   (**AC-R4-4** constructed inconsistency case).
3. W1.3 Controls C1–C3 on synthetic strings (deterministic generators,
   byte-identical rerun **AC-R4-2**).
4. W1.4 C4 WTI case incl. surrogate null gates per Addendum A1 **as amended by
   A3** (Tier 1 Bernoulli(p̂) marginal-matched; Tier 2 circular-block shuffle,
   block = 20 trading days; claim gate = BOTH tiers' 99th percentiles); profile
   figure renders raw timeline (**AC-R4-6**).
5. W1.5 Results write-up under label discipline ("codelength under G",
   "mechanism under F"); every recovery claim elementwise (**AC-R4-3**).

Implementation home: Python-first (`src/analysis/r4_segment_grammar.py` +
tests) unless a task card says otherwise; vendor two-copies rule if
index-deconvolution sources are touched; record PYTHONHASHSEED for any
hash-order-sensitive output.

## Intake queue (registered, unowned)

- n>16 trajectory-route validation experiment (promoted from T4.2 backlog).
- Regeneration producers for any FINDINGS rows adjudicated "re-runnable"
  during the 2026-08-25 dossier pass (see imp-prices
  `results/ledger_lint_full/adjudication_dossier.md`).
- R1/R3 application arms (literature .bnet head-to-head; E. coli
  declared-semantics synthesis). R2 stays out unless forced.
- OEIS-thread context exploration (roadmap Origin, future context only).

- **W0.5 — artefact wiring, formerly "T5.1.v2" (adopted 2026-09-02, AUDIT02/P6).**
  `papers/method/artifact_baseline/artefacts.json` carries 3 COVERED and 5
  PENDING groups, every pending one routed to a task called `T5.1.v2`. That task
  existed in NO plan: not as a numbered task in `AUDIT_FIXING_PLAN_01.md`, and
  nowhere in this file. The plan was BOARD-COMPLETE with the debt unowned. It is
  adopted here under a real id.

  The five groups, and what AUDIT02 already changed for each:
  1. `method_paper` mixed-overlap tables — producer `mixed_interaction_10node.wl`.
     **Now runnable**: it had never executed under `-script` (a `$Path` bootstrap
     one level too shallow, fixed in AUDIT02/A1) and reproduces the anchors
     `d_q=21, c_q=10, mu_q=11, R_q=2048`; S1 `10/7/3/8`; S2 `14/10/4/16`.
  2. `method_paper` corroboration constants — producer `corroboration_6node.wl`,
     exits 0.
  3. `method_paper` scalability tables — producer
     `papers/method/code/scalability_resource_envelope/scalability_resource_envelope.py`
     (note: `artefacts.json` records a path that does not exist; the file lives in
     the `scalability_resource_envelope/` directory). Exits 0; median `|C_q| = 10`
     at n = 30, 60, 80, 200.
  4. `comp_paper` attractor statistics — `generate_paper_outputs.wl` is exit-gated
     and passes; only the `.tex` marker embedding remains.
  5. Remaining appendix tables — markers as each producer is wired.

  Blocking work is therefore only the marker embedding and the `checks` entries,
  not the producers. Each pending entry also carries `id: null`, against the
  file's own rule that an inventory entry be identified; give each a real id when
  wiring it.

## Author gates

- Any catalogue growth (dated amendment + catalogue cost paid in code).
- Any change to frozen thresholds/addenda.
- First results readout of C4 before any external claim.

## Log (append-only)

- 2026-08-25 PLAN-OPENED v0.1 at protocol freeze. Intake as above. No tasks
  executed yet.
- 2026-08-25 v0.2 — adversarial review remediation (pre-result, therefore not
  tuning): PROTOCOL Addendum A3 landed (C1→rule 150; C3→[150,232,150,105]/
  [90,150]; C2 ≥1.00; A1 two-tier null; expressivity pinned at 46/256 via
  mirror-tested catalogue `567b170`; envelope re-derived `d1ef6d5` — w=16
  P(any)=1.67e-4±2.9e-5, E[raw]≈1.2 @7000 obs). Wave 0 unchanged; W1.3/W1.4
  generators must consume catalogue_from_gates.json only (mirror test is the
  authority chain).
