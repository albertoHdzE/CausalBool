# AUDIT02 Phase 2 — real-example verification, and the fallthrough decision

## Context

Phase 1 is committed and pushed (`f17e839..091797b` on `fixing`; revert point is
`f17e839`). It fixed the analytic query surface (4/12 → 12/12 families), closed
the cross-language parity hole (45/45 → 135/135 with CANALISING covered), and
propagated `strict` / `tiePolicy` outward.

All of that was verified against **synthetic enumeration** — truth tables,
symmetric differences, random small networks. The author's position is that only
**real examples with known expected values** can settle correctness, and that is
right: the current evidence shows no *tested* result moved, which is not the same
as showing no *published* result moved. Five of eight flagship artefact groups in
`papers/method/artifact_baseline/artefacts.json` are still PENDING, so the
paper's headline anchors are pinned by a change-detector, not reconciled to a
producer.

Two decisions depend on that evidence: whether the Phase-1 changes disturbed any
published number, and whether to harden `Gates.m`'s silent `True, 0` fallthrough.

**A finding from this exploration changes the shape of the second decision.**

### Finding H — the bio corpus contains gates outside the twelve, and they may reach the canonical engine

`data/bio/processed/*.json` (234 networks) carries these node gate labels:

```
CUSTOM 2486 · IDENTITY 762 · unknown 550 · INPUT 151 · dual 14
```

None is one of the twelve families. `Integration`Gates`ApplyGate` matches none of
them and returns a silent `0` via `True, 0` (`Gates.m:50`).

`src/Packages/Integration/BioExperiments.m:110` passes `dynamic[[i]]`, taken
straight from `net["dynamic"]` (line 124), into `Integration`Gates`ApplyGate`
with no validation. If the corpus `gates` field reaches `net["dynamic"]`
unmapped, then attractor, knockout and essentiality results are computed with
roughly 3,949 node instances silently forced to 0.

For `IDENTITY` and `INPUT` a silent 0 is not merely "unsupported" — it is
**wrong**. The project's own separate implementation agrees:
`src/integration/bio_D_experiment.py:272-277` returns `inputs[0]` for both.

This also means gate semantics still exist in **three** unreconciled places
beyond the ones Phase 1 fixed:

| implementation | IDENTITY / INPUT semantics |
|---|---|
| `src/Packages/Integration/Gates.m` | silent `0` (via fallthrough) |
| `src/integration/bio_D_experiment.py:272` | `inputs[0]` — correct |
| `src/integration/NatureBDM.wl:121,169` | own `INPUT`/`CONST`/`ERROR` handling |
| `src/scripts/PhaseTransitionExperiment.m:25`, `BehavioralKnockoutAnalysis.m:56` | explicit `Return[0]` guard |

Whether this is a live scientific defect or a dormant one turns entirely on
whether the corpus `gates` field reaches `ComputeNextState`. That is an empirical
question, and A3 below answers it before anything is changed.

---

## Plan

**Sequencing (author decision, 2026-09-02):** Finding H is probed **first**,
before Phase A, because its answer reorders everything after it. Phase A2 runs
the full before/after against a temporary worktree at `f17e839`.

### Phase A0 — Settle Finding H first (read-only probe, no code change)

Answer one question: **do non-canonical gate labels actually reach
`Integration`Gates`ApplyGate` on a live bio path?**

Method — trace the corpus field through to the call site, without editing anything:
1. Read `data/bio/processed/*.json` and establish whether the `gates` field is
   what becomes `net["dynamic"]` (`BioExperiments.m:124`), or whether a mapping
   step intervenes. Follow the actual producer of the `net` association.
2. Build `net["dynamic"]` exactly as `RunBioNetwork`/`ComputeNextState` does and
   report the distribution of gate strings that would be passed to `ApplyGate`.
3. For any non-canonical label found, evaluate `ApplyGate[label, inputs, <||>]`
   directly and record what it returns.

Outcomes and consequences, declared in advance:
- **Dormant** (no non-canonical label reaches the call site) → record the
  provenance so the question does not recur; continue to Phase A unchanged.
- **Live** → this is a **P0 scientific defect**: bio attractor, knockout and
  essentiality results computed through `ComputeNextState` used ~3,949 node
  instances forced to 0, including `IDENTITY`/`INPUT` where 0 is demonstrably
  the wrong answer (`bio_D_experiment.py:272-277` returns `inputs[0]`). It then
  outranks the method-paper verification, and any published bio number must be
  restated. **Stop and report before changing anything.**
- **Not wired** (corpus never feeds this path) → record where the bio results
  actually come from.

### Phase A — Real-example verification against known anchors

The flagship producers all exist and use the code Phase 1 touched:

| producer | engine used | anchors it should reproduce |
|---|---|---|
| `papers/method/manuscript_computational/generate_paper_outputs.wl` | `CausalBoolCore.wl` (changed) **+** `Integration`Gates`` | self-verifying; `Exit[1]` on failure (line 408) |
| `papers/method/code/mixed_interaction_10node/mixed_interaction_10node.wl` | `Integration`Gates`` + `IndexSetAnalytic` | d_q=21, c_q=10, μ_q=11, R_q=2048; S1 10/7/3/8; S2 14/10/4/16 |
| `papers/method/code/mixed_interaction_10node/dynamical_landscape_10node.wl` | `ApplyGate` | \|Im(F)\|=206, 4 attractors, basins 488/320/204/12 |
| `papers/method/code/corroboration_6node/corroboration_6node.wl` | own AND closed form | 6-node AND corroboration |
| `papers/method/code/scalability_resource_envelope/scalability_resource_envelope.py` | Python | median \|C_q\|=10 for T3 at n=30,60,80,200 |

**A1 — run all five and check against the recorded anchors.** `D_formula=135.66`,
`C_formula=23`, `ZIP=10016`, `H_total=10229.61`, `BDM=580.01`. Report each as
observed-vs-expected, elementwise where the object is a set. A number that merely
"looks right" is not a pass; the basin vector and the index sets are compared
member by member.

**A2 — the decisive before/after.** Create a read-only `git worktree` at
`f17e839` (pre-Phase-1), run the identical five producers there, and diff the
outputs against A1 **elementwise**. This is the only thing that can actually
answer "did our changes disturb a published result". Expected outcome, stated in
advance so it is falsifiable: **byte-identical outputs**, because every Phase-1
behaviour change lies on a path that previously returned `Null` or a provably
wrong set, and no published number can have come from such a path. If anything
differs, that difference is the finding.

*(A3 moved to Phase A0 above, by author decision — it runs first.)*

### Phase B — the `Gates.m` fallthrough decision, made on evidence

**B1 — measure the blast radius, do not guess.** Wrap `ApplyGate` in a logging
shim (in a scratch script, not in the repo) and run the full MUnit suite plus all
five producers, recording every distinct `gate` string it receives. There are 81
call sites; this converts "would it break anything" from an opinion into a list.

**B2 — decide from B1 plus A3.** The options are genuinely different depending on
the evidence, so the decision is deferred to that point rather than pre-committed
here. If no live path passes a non-canonical gate, hardening is zero-impact and
should simply be done. If bio paths do, then the right fix is not a bare
`Failure` — it is **correct semantics for `IDENTITY` and `INPUT`** plus a loud
failure for genuinely unknown labels, which is a larger and more valuable change.

### Phase C — carried forward from Phase 1, unchanged

P4d (adjudicate `filterByCondition`, `findPatternIndices`,
`inIdxProducingOutsToDecimal`), then P4e (archive the `src/causal/` island),
P5 (add `make verify-paper` to the closure triad; add a code-conformance pass to
the glossary gate), P6 (adopt the orphaned `T5.1.v2` debt), P7 (archive the three
dead hardcoded-number scripts). None may start before Phase A completes.

---

## Verification

```bash
# A0 — Finding H probe (read-only; runs FIRST)
#   trace data/bio/processed/*.json "gates" -> net["dynamic"] -> ApplyGate,
#   report the gate-string distribution at the call site, and evaluate
#   ApplyGate on each non-canonical label directly.
#   PASS = no non-canonical label reaches ApplyGate.
#   Any label that does => STOP, report, do not proceed to Phase A.

# A1 — flagship producers (run from repo root)
HOME=$HOME /Applications/Wolfram.app/Contents/MacOS/WolframKernel -script \
  papers/method/manuscript_computational/generate_paper_outputs.wl; echo "exit=$?"   # must be 0
HOME=$HOME .../WolframKernel -script papers/method/code/mixed_interaction_10node/mixed_interaction_10node.wl
HOME=$HOME .../WolframKernel -script papers/method/code/mixed_interaction_10node/dynamical_landscape_10node.wl
HOME=$HOME .../WolframKernel -script papers/method/code/corroboration_6node/corroboration_6node.wl
venv/bin/python papers/method/code/scalability_resource_envelope/scalability_resource_envelope.py

# A2 — before/after against the pre-Phase-1 tree (read-only worktree)
git worktree add /tmp/cb-pre f17e839
#   ... run the same five there, then diff every produced JSON/CSV elementwise
git worktree remove /tmp/cb-pre

# B1 — blast radius
#   scratch shim over Integration`Gates`ApplyGate, then:
zsh tests/MUnit/run-tests.sh --all

# standing regression bar (must not move)
zsh tests/MUnit/run-tests.sh --all        # OK=52 FAIL=1 TOTAL=53, sole red TopologiesTests
(cd index-deconvolution && ../venv/bin/python -m pytest -q)   # 146
(cd imp-prices && .venv/bin/python -m pytest -q)              # 97
python tools/snapshot_paper_numbers.py --check                # 109 identical
make verify-paper                                             # 3 covered, 5 pending
```

**Acceptance for Phase A:** every anchor reproduced at its recorded value, and
A2 byte-identical between `f17e839` and `HEAD`. Any deviation is reported with
its symmetric difference and location before any further change is made.
