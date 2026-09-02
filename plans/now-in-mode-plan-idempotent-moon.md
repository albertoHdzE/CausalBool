# Adversarial code audit — collisions, dead code, hardwiring, and inheritance risk

## Execution status (2026-08-26)

**Done — P4a, P4b, P4c, P1, P2, P3.** Evidence:

| check | result |
|---|---|
| `createRepertoireByResult` vs `ApplyGate`, elementwise + order-sensitive | 96/96 identical, 12 families |
| planted-defect control (pre-fix code, same assertions) | **64/92 fail**, 9 families; 4 with *agreeing counts* |
| non-regression on previously-working gates | 28/28 byte-identical; only MAJORITY `res=0` changed (the fix) |
| analytic `IndexSet` vs repaired exhaustive baseline, via Φ | 43 gate×arity pairs, **0 mismatches** |
| `CausalBoolCore.wl` vs `Gates.m` | 2462/2464 identical (2 = out-of-range `canalisingIndex`, unevaluated both sides) |
| Python `causalbool.py` vs `Gates.m` | **2462 evaluations, 0 mismatches** |
| cross-language parity bundle | **135/135**, all 12 gates (CANALISING 105, was 0), params `k`/`strict`/`tiePolicy`/canalising triple |
| MUnit suite | `OK=52 FAIL=1 TOTAL=53` |
| subproject suites | 146 / 97 / 41 / 47 / 28 — all at recorded values |
| paper gates | 109 identical · GLOSSARY clean · verify-paper 3 covered |

**Suite ledger reconciliation** (baseline at `f17e839` was `OK=47 FAIL=4 TOTAL=51`):
`+2 TOTAL` = the two tests added here; `−3 FAIL` = **your developer's uncommitted
R4/W0.3 test fixes**, not this work — `KOFNNetworkTests` (`anaIdx_k1` parsed as a
Pattern), `IMPLIESNetworkTests` (`Or`/`And` over integers stayed symbolic, so the
empirical arm exported `{}`), `TSK-ARCH-004` (`$VersionString` is not a built-in).
All three were genuine *test* defects. This work introduced zero new failures.

**Not done: P4d, P4e, P5, P6, P7.** The island must not be archived until P4d
adjudicates `filterByCondition`, `findPatternIndices` and
`inIdxProducingOutsToDecimal`.

**New finding raised during execution:** `Gates.m`'s own `ApplyGate` still
returns a silent `0` for an unknown gate (`True, 0`), so the companion file is
now *stricter* than the canonical engine. Same defect class as the one just
fixed; not changed here because it is a live engine path with a wider blast
radius than this plan authorised.

## Context

`AUDIT_FIXING_PLAN_01` closed honestly (verified last session: triad reproduces,
history is append-only, no post-freeze tuning). This audit asks a different
question: not *was the process clean*, but *is the implementation sound enough
that sibling projects can inherit from it safely*.

The answer is **no, not yet** — for one specific and fixable reason. The claim
"validated forward model" that the siblings rely on rests on a parity proof
whose reference implementation is missing the one gate the siblings actually
use in production.

Nothing here is fabricated science or a fake result. The defects are
**scope overreach in validation claims**, **three divergent copies of one
engine**, and **two closure gates that prove less than their placement
implies**.

---

## Findings

### A. CRITICAL — the parity proof has a hole exactly where the siblings are exposed

Three implementations of one engine, with different gate sets:

| | `src/Packages/Integration/Gates.m` (canonical) | `papers/method/code/lib/CausalBoolCore.wl` (parity reference) | `index-deconvolution/src/causalbool.py` (inherited) |
|---|---|---|---|
| Families | **12** incl. CANALISING | **11 — CANALISING absent** | 12 incl. CANALISING |
| Unknown gate | `True, 0` silent | `True, 0` silent | `raise ValueError` |
| KOFN `strict` | honoured (T4.7 fix) | ignored | ignored |
| MAJORITY `tiePolicy` | honoured | hardcoded strict | hardcoded strict |
| Extra gates | — | — | `REGULATORY`, `REGULATORY_DNF` |

Evidence:
- `CausalBoolCore.wl` has no `CANALISING` branch; it falls through to `True, 0`,
  so a CANALISING node **silently evaluates to 0** rather than erroring.
- `index-deconvolution/crosscheck/cases.json` — 45 cases, gate frequency
  `{NAND 32, NOT 37, AND 29, OR 38, NIMPLIES 29, XNOR 32, IMPLIES 25,
  MAJORITY 21, XOR 34, KOFN 22, NOR 16}`. **Zero CANALISING cases.**
  Param keys exercised: `{k}` only — `strict` and `tiePolicy` never touched.
- `imp-prices/src/imp_prices/gate_network.py:12` describes
  `vendor/causalbool.py` as *"the validated forward model"*.
- CANALISING is instantiated **12 times** across `imp-prices` +
  `index-deconvolution` experiment code.

So the README claim (`index-deconvolution/README.md:138`, *"Python forward model
proven equivalent to the Wolfram reference: 45 / 45"*) is true as stated but
**chains to the reduced reference**, and its coverage excludes the gate the
downstream work depends on. This is the inheritance risk in concrete form.

### B. HIGH — a canonical bug fix was never propagated to the shipped companion code

`Gates.m:31–34` carries the T4.7 fix, with its own comment: *"ApplyGate silently
dropped `strict`, diverging from the closed-form engine exactly when
strict=True."* Neither `CausalBoolCore.wl` nor `causalbool.py` received it —
both are `Count[inputs,1] >= k`. Same story for MAJORITY `tiePolicy`.

Currently **latent**: no downstream call site sets `strict` or `tiePolicy`.
But `CausalBoolCore.wl` is the reproducible companion code the method paper
ships, so a reader following the paper reproduces the pre-T4.7 behaviour.

### C. HIGH — `causalbool.py` contradicts itself and its own docstring

- `GATE_TYPES` (line 41) declares 12 families; the body also implements
  `REGULATORY` (line 92) and `REGULATORY_DNF` (line 104), which are in neither
  Wolfram engine and not in `GATE_TYPES`.
- Docstring (line 45): *"Semantics are identical to `Integration`Gates`ApplyGate`"*
  — false in at least three respects (KOFN strict, MAJORITY tiePolicy, the two
  extra gates). MAJORITY's `count(1) > count(0)` **is** algebraically equal to
  Gates.m's `ones >= Floor[d/2]+1` for all arities — that one is fine.

### D. MEDIUM — a self-contained legacy island, not a drifting clone

**Corrected from the first pass of this audit.** The initial reading — "T1.4's
renames landed on the dead copy only, so the live engine still carries the old
terminology" — was wrong, and the correction matters because it changes what is
safe to do.

Surgical determination:

- `src/integration/Alpha.m` (6395 lines, 136 definitions) is **live**: `Get` at
  `src/Packages/Integration/Alpha.m:5` and `Experiments.m:6`.
- `src/causal/CausalBool.m` (6296 lines, 129 definitions) is loaded by **nothing**.
  `grep -rn "src/causal"` over all `*.m *.wl *.py *.sh *.json Makefile` returns no loader.
- They share ancestry through `cba2eec` (2026-08-22) and then received
  **different** later commits — neither is a superset:
  - `Alpha.m` ← `7c56dc6` T4.1: ORDERING fixes **and the F24 stale-`resOp` guards**
    (`Failure["UnsupportedGate"]` instead of silently reusing the previous node's result).
  - `CausalBool.m` ← `316ce22` T1.4: terminology only.
- **7 functions are defined only in `CausalBool.m`**: `findANDIndicesFormula`,
  `findPatternIndices`, `findInputsProducingOutput`, `combineInsIdxProducingOuts`,
  `inIdxProducingOutsToDecimal`, `filterByCondition`, `v2`.
  **14 are defined only in `Alpha.m`**, including the core `createRepertoires`
  and the whole `runDynamic*` family.
- Every one of those 7 is referenced by exactly two files: `src/causal/CausalBool.m`
  and its own companion notebook `src/causal/CausalBool.nb`. Nothing outside
  `src/causal/` touches them. The directory is a closed island
  (`CausalBool.m` + `.nb` + `.vsnb`).
- **Why the rename counts differed:** the T1.4 edits sit at `CausalBool.m:2262–2349`,
  *inside* `findPatternIndices` and `findANDIndicesFormula` — two of the seven
  island-only functions. `Alpha.m` has **zero** hits for `pivot = Total`, `"Pivot"`
  or `pivots`. The live engine never carried the technical "pivot" sense, so
  nothing was left un-renamed. T1.4 was complete.

**Consequence:** `Alpha.m` is unambiguously the file to keep. It is the only one
loaded, it holds the T4.1 safety hardening and the core repertoire functions, and
it already satisfies the constraint that the retained engine must not use "pivot"
outside the financial sense.

One live loose end: `GOVERNANCE/GLOSSARY.md:236` cites
`src/causal/CausalBool.m findANDIndicesFormula`. Archiving without repointing
that citation would recreate exactly the dangling-citation defect T1.4 existed
to remove.

### D2. CRITICAL — the analytic query surface is gate-incomplete in LIVE code

This is the finding that matters most, and it is not about filing. Tracing the
7 island functions showed most are **old names for live functions**, not lost
capability — but the trace exposed a defect in the live code itself.

`Alpha.m`'s `combiningRepersWithSharedInputs` is the island's
`combineInsIdxProducingOuts` with one substitution
(`findInputsProducingOutput` → `createRepertoireByResult`); the usage examples
are character-identical (`{1,3,5,6},"OR",1,{1,5,7,3},"AND",1` → `DecRep {85,117}`).
It is **live**, called at `Alpha.m:2491,2499`.

But the function it depends on, `createRepertoireByResult`, has a `Which` with
branches for **only 4 gates — XOR, OR, AND, MAJORITY**. The other eight
(NAND, NOR, XNOR, NOT, IMPLIES, NIMPLIES, KOFN, CANALISING) match no branch, so
Mathematica's `Which` returns **`Null`** — silently, with no message. It then
carries the island's bug verbatim: the MAJORITY branch tests `== 1` and
**ignores the requested `res`**, so asking for inputs producing 0 returns those
producing 1.

This is precisely the capability the papers need — *"here are the exact inputs
producing this output, analytically, rather than by enumerating 2^n"*. It works
for a third of the gate catalogue and fails silently for the rest.

**Capability map (evidence-based, not assumed):**

| island function | live counterpart | status |
|---|---|---|
| `combineInsIdxProducingOuts` | `combiningRepersWithSharedInputs` (`Alpha.m:2117`) | renamed; live; more overloads |
| `findInputsProducingOutput` | `createRepertoireByResult` (`Alpha.m`) | renamed; live; **4/12 gates + MAJORITY bug** |
| `v2` | — | in-file refactor of `combineInsIdxProducingOuts`; superseded by the same. Note it drops the `Reverse[Reverse[#]&/@…]` the original applies — a possible ordering divergence |
| `findANDIndicesFormula` | `IndexSetAnalytic` / `IndexSetNetwork` (`Gates.m:171,178`) | superseded, all 12 gates, MUnit-covered — **needs numerical confirmation** |
| `inIdxProducingOutsToDecimal` | `inOutBin2Dec` / `inOutBin2DecReverse`? | **different signatures — equivalence NOT established** |
| `filterByCondition` | none found | **no live counterpart** |
| `findPatternIndices` | none found | **no live counterpart** |

### E. MEDIUM — two closure-triad gates prove less than their placement implies

- `tools/check_glossary_sync.sh` diffs our `GLOSSARY.md` against the sibling's
  `GLOSSARY.md`. It verifies **document mirroring**, never code conformance —
  which is why finding D passes it undetected.
- `tools/snapshot_paper_numbers.py --check` re-extracts numbers from the two
  `.tex` files and diffs against a snapshot **of those same `.tex` files**. It is
  a manuscript change-detector, not a correctness check.
- The only real number-correctness gate, `tools/verify_paper_artefacts.py`
  (`make verify-paper`), was **not in the closure triad**. It passes today:
  `PASS four_paths_table / mechanism_vs_dataset_table / comp_validation_summary`.

### F. MEDIUM — orphaned closure debt

`papers/method/artifact_baseline/artefacts.json`: **3 COVERED, 5 PENDING**, every
pending item routed to a task called **`T5.1.v2`**, which:
- is not a numbered task anywhere in `AUDIT_FIXING_PLAN_01.md`, and
- appears nowhere in `SUCCESSOR_PLAN_R4.md` (not Wave 0, Wave 1, or the intake queue).

The plan is BOARD-COMPLETE while this debt has no owner. The 5 pending entries
also carry `id: null`, against the file's own rule that inventory entries be identified.

### G. LOW — dead scripts carrying hardcoded numbers

Referenced by nothing (`src/scripts/`): `compute_bdm_from_d5.py:162`
*"Gzip ratios from table (hardcoded for now)"*; `verify_bdm_from_mathematica_table.py:129`
*"hardcode them if we know them"*; `simulate_factorisation.py:46` *"Gates (dummy)"*.
Harmless today; a provenance trap if anyone reruns them.

### Checked and clean — no action

- **Vendor two-copies rule honoured**: `index-deconvolution/src/{causalbool,deconvolution}.py`
  are byte-identical to `imp-prices/vendor/` copies.
- **causalNet CTM boundary is correct**: `official.py:94` raises
  `NotImplementedError("only the 4x4 CTM table is ported here")` rather than
  silently degrading — a faithful port boundary, matching the paper's own R code.
- **The ZIP=1600 blocker is resolved**: both manuscripts now carry `10016`.
- **No mocks or simulated results in replication logic.** Every `mock_`/`dummy`/
  `NotImplementedError` hit outside the above sits in declared vendored trees
  (`src/external/ccapi/`, `imp-pathinfo-paper/reference/`).

---

## Plan

**Execution order: P4a–P4c first, then P1–P3, then P4d–P4e, then P5–P7.**
P4a is a live-code defect in the capability the papers are built on; P1 is the
sibling-inheritance blocker. Both precede any archiving or documentation work.

### P1 — Close the parity hole (blocking for sibling inheritance)

1. Add CANALISING to `papers/method/code/lib/CausalBoolCore.wl`, transcribed from
   `Gates.m:35` (`myCanalising` — note the non-canalised branch is `myOr[list]`,
   **not** a constant default).
2. Replace the `True, 0` fallthrough in `CausalBoolCore.wl` with an explicit
   failure, mirroring the T4.1 hardening already applied in `Alpha.m`
   (`Failure["UnsupportedGate"]`). Silent 0 is the dangerous pattern.
3. Extend `index-deconvolution/crosscheck/generate_crosscheck_cases.py` to
   cover CANALISING (all `canalisingIndex` × `canalisingValue` ×
   `canalisedOutput` combinations), plus `KOFN.strict` both ways and
   `MAJORITY.tiePolicy` both ways. Regenerate `cases.json`, rerun
   `crosscheck/wolfram_equivalence.wl`, commit the new `wolfram_result.json`.
4. Correct `index-deconvolution/README.md:138` to state the gate coverage and
   parameter coverage of the proof, not just the case count.

### P2 — Propagate the T4.7 / D-3 semantics

Add `strict` to KOFN and `tiePolicy` to MAJORITY in both `CausalBoolCore.wl` and
`index-deconvolution/src/causalbool.py`, matching `Gates.m:21–34` exactly. Apply
to `imp-prices/vendor/causalbool.py` **in the same commit** (vendor two-copies rule,
AC-R4-7). Defaults must preserve today's behaviour so no existing result moves.

### P3 — Repair `causalbool.py`'s self-consistency

Add `REGULATORY` and `REGULATORY_DNF` to `GATE_TYPES`, and rewrite the
`apply_gate` docstring to say precisely which subset is Gates.m-equivalent and
which two gates are Python-only extensions with no Wolfram counterpart.

### P4 — Restore the analytic query surface to full gate coverage (highest value)

**Archiving is the last step, not the first.** The island may not be retired
until every capability in it is demonstrably present and correct in live code.

**P4a — Fix `createRepertoireByResult` (`src/integration/Alpha.m`).**
Reimplement it over all 12 families by delegating to the canonical
`Integration`Gates`ApplyGate` rather than re-encoding gate logic inline — this
removes the fourth copy of gate semantics rather than extending it. Fix the
MAJORITY branch to honour `res`. Replace the silent `Which` fallthrough with
`Failure["UnsupportedGate", …]`, matching the T4.1/F24 hardening already applied
elsewhere in this same file. Preserve the existing LSB-first output ordering
(`Reverse[Reverse[#]&/@Tuples[…]]`) exactly — it is load-bearing for `DecRep`.

**P4b — MUnit coverage for the query surface.** New test asserting, for every one
of the 12 families and both output values, that `createRepertoireByResult`
returns exactly the input set for which `ApplyGate` gives that output —
elementwise symmetric difference, arity 1..4. This is the test whose absence let
a 4-of-12 gap and a MAJORITY bug live in the engine.

**P4c — Establish the analytic-vs-exhaustive equivalence the papers rest on.**
Confirm numerically that `IndexSetAnalytic` / `IndexSetNetwork`
(`Gates.m:171,178`) reproduce `findANDIndicesFormula`'s decimal-anchor result on
AND, then extend to all 12 gates against the repaired exhaustive baseline.
`tests/MUnit/Mixed/TSK-MIXED-001-FormulaVsExhaustiveTests.m` is the existing
harness for this comparison and should be extended rather than duplicated.
Any mismatch here is a genuine scientific finding, not a filing error.

**P4d — Adjudicate the three unmapped functions.** For `filterByCondition`,
`findPatternIndices` and `inIdxProducingOutsToDecimal`, decide per function:
port into the packaged API with tests, or record as superseded **with the
equivalence demonstrated**. `inOutBin2Dec` has a different signature, so
equivalence with `inIdxProducingOutsToDecimal` must be shown, not assumed.
`filterByCondition` and `findPatternIndices` currently have no live counterpart
at all and are the strongest candidates for porting — `findPatternIndices` is
the closed-form "which rows match this partial pattern" query, which is exactly
the analytic-over-exhaustive demonstration the papers want.

**P4e — Only then, retire the island.** Move `src/causal/CausalBool.m`, `.nb`,
`.vsnb` together to `archive/causal-exploratory/` per the archive policy
(preserve, never delete), with a README recording the capability map above and
the commit that demonstrated each equivalence. Repoint
`GOVERNANCE/GLOSSARY.md:236`. Add a guard that no file outside
`src/integration/Alpha.m` defines `createRepertoires` or `runDynamic`.

Nothing loads `src/causal/`, so P4e is execution-neutral; the suite must be
identical before and after (`OK=47 FAIL=4 TOTAL=51`). P4a is *not*
execution-neutral and is the step that needs the regression evidence.

### P5 — Strengthen the gates

1. Add `make verify-paper` (`tools/verify_paper_artefacts.py`) as the **fourth**
   member of the closure triad, and say plainly in `BASELINE.md` what each of the
   four proves and does not prove — in particular that the paper-number gate is a
   change-detector.
2. Extend `check_glossary_sync.sh` (or add a companion) with a code-conformance
   pass: assert the retired terms do not appear in live engine files.

### P6 — Adopt the orphaned debt

Register the 5 PENDING artefact groups in `SUCCESSOR_PLAN_R4.md`'s intake queue
under a real task id, give each entry a non-null `id` in `artefacts.json`, and
either define `T5.1.v2` or repoint the references to the new id.

### P7 — Archive the dead scripts

Move the three `src/scripts/` files in finding G to `archive/` per the project's
stated archive policy (preserve, do not delete).

---

## Verification

Run in this order; every step must be green before the next.

```bash
# P4a/P4b — the analytic query surface, all 12 gates, both output values
zsh tests/MUnit/run-tests.sh --section Analysis
# new test must show: for every family x arity 1..4 x res in {0,1},
# createRepertoireByResult == {inputs : ApplyGate == res}, symDiff empty.
# Pre-fix this fails for NAND NOR XNOR NOT IMPLIES NIMPLIES KOFN CANALISING
# (returns Null) and for MAJORITY res=0 (returns the res=1 set).

# P4c — analytic vs exhaustive
zsh tests/MUnit/run-tests.sh --section Mixed   # extended FormulaVsExhaustive

# P1/P2 — cross-language parity, now with CANALISING + strict + tiePolicy
cd index-deconvolution && python crosscheck/generate_crosscheck_cases.py
HOME="$HOME" CB_CASES=.../cases.json CB_CORE=.../CausalBoolCore.wl \
  CB_OUT=.../wolfram_result.json \
  /Applications/Wolfram.app/Contents/MacOS/WolframKernel -script crosscheck/wolfram_equivalence.wl
# expect all_match == true, n_cases > 45, CANALISING present in the case set

# P2 — vendor copies must remain byte-identical
diff index-deconvolution/src/causalbool.py imp-prices/vendor/causalbool.py

# regression: no existing result may move
zsh tests/MUnit/run-tests.sh --all          # expect OK=47 FAIL=4 TOTAL=51, same four owned reds
(cd imp-prices && .venv/bin/python -m pytest -q)          # expect 97 passed
(cd index-deconvolution && ../venv/bin/python -m pytest -q)  # expect 146 passed
(cd imp-pathinfo-paper && .venv/bin/python -m pytest -q)   # expect 41 passed
(cd imp-causalNet-paper && .venv/bin/python -m pytest -q)  # expect 47 passed
(cd imp-causal-paper && .venv/bin/python -m pytest -q)     # expect 28 passed

# P5 — all four gates
python tools/snapshot_paper_numbers.py --check   # 109 entries identical
zsh tools/check_glossary_sync.sh                 # clean
make verify-paper                                # 3 covered, 5 pending
```

Acceptance: parity `all_match == true` **with CANALISING in the case set**, and
every suite above at its recorded value — a changed count means P2's defaults
were not behaviour-preserving.
