# ORDERING — Canonical bit-ordering convention for CausalBool

**Status:** ACTIVE · Established by **AUDIT_FIXING_PLAN_01 / T4.1** (2026-08-25).
**Authority:** on *definitions*, `GOVERNANCE/GLOSSARY.md`; this document governs
*ordering conventions* for all WL code in `src/Packages/Integration/`, the legacy
bridge `src/integration/Alpha.m`, and every consumer comparing index sets to
row-repertories. The paper declares LSB primary (:181) with MSB transported by Φ
(Thm :1451); **the code now obeys that declaration by contract, not by memory.**

---

## §1 Canonical internal representation: LSB-first

Row *r* of any repertoire (1-based, r = 1 … 2ⁿ) corresponds to integer x = r − 1 with

- **coordinate i (node i) = digit i of `Reverse[IntegerDigits[x, 2, n]]`**, i.e. node 1 is
  the least-significant bit; weight of coordinate i is w(i) = 2^(i−1);
- one-set index of a configuration with on-set S ⊆ {1…n}: `1 + Σ_{i∈S} 2^(i−1)`.

This is the enumeration produced by `allPosibleInputsReverse`,
`CreateRepertoiresDispatch`, and `RunDynamicDispatch`, and is the native output
space of `IndexSetAnalytic`. It is the **only** representation in which raw row
indices from different producers may be compared without transport.

## §2 The Φ transport rule (exactly once, at interop boundaries only)

Φ(j, n) = `1 + FromDigits[Reverse[IntegerDigits[j − 1, 2, n]], 2]`
(`Integration`IndexAlgebra`Phi`; private twin `PhiIndex` inside Gates.m).

1. Φ is an involution: Φ∘Φ = id (verified by execution, T4.1 probe).
2. Apply Φ **exactly once** when moving an index set between an MSB-enumerated
   producer and an LSB-enumerated consumer (or back).
3. Applying it twice (or zero times where required) is a defect class with a known
   signature: on the mixed-10 benchmark it yields accuracy 0.6 with 4096 mismatched
   cells (probe B/C, below) — elementwise near-chance agreement.
4. Consumers must NOT keep per-call-site Φ bookkeeping where a producer already
   returns canonical (LSB) sets. Reference application:
   `TSK-MIXED-001-FormulaVsExhaustiveTests.m` `indexSetPredict` — the single,
   commented transport between MSB-row `IndexSetNetwork` output and LSB rows.

## §3 Public-function contract table

| Function | Row/input enumeration | Notes |
|---|---|---|
| `Gates`ApplyGate | order-agnostic (takes explicit input list) | gate semantics only |
| `Gates`TruthTable[gate, arity] | **MSB** (`IntegerDigits[x,2,d]`) | arity-local table |
| `Gates`IndexSet[gate, arity] | **MSB** | closed families transported internally LSB→MSB via `PhiIndex` exactly once; KOFN/CANALISING branches native MSB |
| `Gates`IndexSetNetwork[gate, n, Ic] | **MSB** rows of the n-bit space | params interpreted **Ic-relative** (§5) |
| `Gates`IndexSetAnalytic[n, Ic, gate] | **LSB-canonical** (w(i)=2^(i−1)) | closed-form engine; sorted, 1-based; `$Failed` for unknown family |
| `IndexAlgebra`OneBandIndices/ZeroBandIndices | **MSB** | band indices over `IntegerDigits` enumeration |
| `Experiments`CreateRepertoiresDispatch / RunDynamicDispatch | **LSB** (`Reverse[IntegerDigits]`) | packaged dispatch |
| legacy Alpha.m `createRepertoires` / `runDynamic` / `runDynamicHD` / file variants | **LSB** via `allPosibleInputsReverse` | supported gates only since T4.1 (§6) |
| `BioExperiments.m` `ComputeAttractors` state enumeration | **LSB-canonical** (`Reverse[IntegerDigits[x,2,n]]`) | migrated 2026-09-02, AUDIT02/W0.1; §7 |

Rule of thumb: anything "table-like" (`TruthTable`, `IndexSet`, band indices,
`Tuples`) is MSB; anything "repertoire-like" (dispatch repertoires, legacy Alpha,
closed-form analytic sets) is LSB. When in doubt, grep the enumeration line and add
the finding to Appendix B's spot-check list.

## §4 F36 closure — CANALISING coordinate convention (resolved)

**Declared convention: `canalisingIndex` is interpreted in Ic-relative coordinates**
— a position within the ordered connected-input list actually handed to the gate —
identical to how every other gate parameter behaves under `Part[row, Ic]`.

This matches `myCanalising` (package), the closed-form CANALISING branch of
`indexSetAnalyticCore`, and `ApplyGate`'s contract generally.

Fixed in T4.1: `Gates`IndexSetNetwork`'s CANALISING branch previously reordered the
row to place the canalising bit first while passing the original (absolute-valued)
`canalisingIndex` through — correct only when that value equalled position 1 of Ic.
The branch now evaluates `ApplyGate` on `Part[#, Ic]` like every other family.
Pinned elementwise by `tests/MUnit/Gates/TSK-GATES-014-CanalisingCoordTests.m`
(40-case grid including ci ∉ {first position}); the MUnit fast-path copy in
TSK-MIXED-001 was aligned (default case provably identical; benchmark sets no
CANALISING parameters — published numbers invariant, verified by suite + Summary).

Documented exceptions — **CLOSED 2026-09-02, AUDIT02/W0.2.**
`tests/MUnit/Mixed/TSK-MIXED-001-Comparison.m` and
`TSK-MIXED-001-OnPossibleBehaviour.m` read network-absolute indices in their
local CANALISING branches. Both are now migrated to the Ic-relative reading
(`bits[[ci]]`, relative default 1), so §4b holds with no exception.

The alignment landed with the executed test §4 required:
`tests/MUnit/Mixed/TSK-MIXED-001-CanalisingExceptionTests.m`, 8,960 cases over
n = 5, every support of size 2–4, every relative `ci`, both canalising values
and both canalised outputs. Three assertions, of which the second is what makes
the first mean anything:

| assertion | result |
|---|---|
| POSITIVE — migrated relative reading vs `ApplyGate` on `Part[row,Ic]` | 0 mismatches |
| NEGATIVE — old absolute reading vs the engine | **1,440 mismatches** (the divergence was real, and the grid reaches it) |
| DEFAULT — relative vs absolute with no explicit `canalisingIndex` | 0 mismatches |

The default row explains why the exception survived: with `ci` defaulting to the
first connected input the two conventions coincide, so the bug was unreachable
until a caller set `canalisingIndex` explicitly. Ledger moves OK=53→54,
TOTAL=54→55; the single red (`TopologiesTests`) is unchanged.

Callers holding network-absolute canalising coordinates translate once at their
boundary: `rel = First@FirstPosition[Ic, ciAbs]`.

## §4b Gate-parameter coordinate conventions (pinned by executed witnesses)

| Parameter | Coordinates | Honored by | Ground-truth form |
|---|---|---|---|
| `canalisingIndex` | **Ic-relative** | myCanalising, indexSetAnalyticCore, IndexSetNetwork (post-T4.1), MUnit fast path | `ApplyGate` on `Part[row,Ic]` |
| `pair` (IMPLIES/NIMPLIES) | **network-absolute** | indexSetAnalyticCore, MUnit vectorPredict | direct connective evaluation on `row[[a]],row[[b]]` |
| `i` (NOT) | **network-absolute** | indexSetAnalyticCore | `(1-row[[ii]])` |
| `k`,`strict` (KOFN) | threshold (+ policy flag, post-T4.7-1) | all sites incl. ApplyGate | `ApplyGate` |

Note the deliberate asymmetry: CANALISING names a connected input by its
*position among connected inputs*; IMPLIES/NIMPLIES/NOT name coordinates by
*absolute network index*. Each convention is single-sourced and pinned by
`papers/method/derivations/verification/*.json`; do not "unify" silently.

## §5 Legacy stale-`resOp` guard (F24)

Every legacy dispatch loop (`runDynamic`, `createRepertoires`, `runDynamicHD`,
`runDynamicInputsFromFile`, `runDynamicFromFileBatches`,
`calculateOneOutptuOfNetwork`) now assigns
`Failure["UnsupportedGate", <|"Gate", "NodeIndex", "Function"|>]` and emits
`AlphaLegacyDispatch::unsupportedgate` for any gate outside its supported set,
instead of silently re-appending the previous node's result. Negative-control
probe: `tools/T41_ResOpGuardProbe.wl` (exit≠0 on any silent case; positive
controls cross-checked against the packaged dispatch, programmatically derived).

## §6 Root cause appendix — the archived `accuracyIndex = 0.51875` (F06/F37)

Corrected understanding, superseding the plan-context suspicion of an
"ordering-bridge mismatch":

1. The archived artifact (`results/tests/mixed001FormulaVsExhaustive/` @ git
   `406a010`, Status.txt dated Sat 22 Nov 2025) contains an **all-zero**
   `OutputsPredictiveIndex.csv`: |ones| = 0 in every node.
2. Its agreement with its own baseline is therefore exactly the baseline
   zero-cell fraction: 1 − 4928/10240 = **0.51875** (5312 zeros). Elementwise diff
   committed at `rootcause/archived_artifact_diff.json`.
3. No ordering scramble reproduces this figure: fresh-executed bridges Φ-omitted
   and Φ-doubled both give accuracy 0.6 (4096 mismatches), while the current
   single-Φ path gives 0 mismatches (accuracy 1.0). Probe:
   `tools/T41_RootCauseProbe.wl` → `rootcause/probe_results.json`.
4. Mechanism class: a superseded script revision whose Index-path silently
   produced no ones (empty one-sets ⇒ the guarded assignment never fires ⇒ score
   collapses to the zero-fraction), preserved because F35 orphaning kept the test
   out of the runner glob so the artifact was never regenerated, and the
   exit-code-only runner hid the FAIL verdict. Exact Nov-2025 source predates git
   history (file first committed 2026-01-01) and is unrecoverable; the mechanism,
   the artifact signature, and the cure (T1.2 fall-through elimination + T1.1
   theorem-paths criterion) are all evidenced.

**Lesson (extends U8):** an accuracy number computed against a baseline has a
degenerate all-zero/all-one twin; any reported accuracy should be accompanied by
its confusion counts or per-node symmetric differences so degenerate agreement is
visible immediately.

## §7 BioExperiments migration path (EXECUTED 2026-09-02, AUDIT02/W0.1)

**Status: done.** `ComputeAttractors` now enumerates
`Reverse[IntegerDigits[x,2,n]]`, so §3 no longer carries an MSB exception.

Executed only after the invariance was *established*, not assumed. The function
was run through its public API over 40 real corpus networks (n = 4…11) under
both enumerations; the attractor sets agree elementwise, **0/40 differing**. The
reason is structural: `states` feeds a `Graph` keyed by state *vectors*, and the
two enumerations are the same set in a different order, so fixed points and
cycles are unchanged. The comparison was proven able to detect a difference by a
planted defect — removing half the state space moves 18/40 — because a check
that has never failed proves nothing. Step 2 of the path below therefore did not
bite: nothing this function returns is keyed by row order.

Two traps were caught on the way, both worth recording because they would
silently invalidate any similar probe:
- `Reverse /@ Tuples[{0,1},n]` is **not** a defect — it permutes the state set
  onto itself, so it is useless as a control.
- `ComputeNextState` is private; calling
  `Integration`BioExperiments`ComputeNextState` reaches a definition-less symbol
  that returns unevaluated. Probes must go through `ComputeAttractors`.

The original path, retained for provenance:

`src/Packages/Integration/BioExperiments.m:126` enumerates states as
`Tuples[{0,1}, n]` (lexicographic ≡ MSB digit order) while downstream metric code
consumes repertoire-style outputs. Migration path when scheduled:

1. Replace `Tuples[{0,1}, n]` with `Reverse[IntegerDigits[x,2,n]]` enumeration
   (canonical LSB rows).
2. Any persisted artifacts keyed by lexicographic row order gain a dated note and,
   where re-imported, a single Φ transport at load time.
3. Attractors/basin outputs keyed by decimal x map unchanged (x = r − 1 either way)
   but their bit-renderings reverse; regenerate figures rather than transposing.

Until migrated, consumers bridging BioExperiments state lists to repertoire rows
must apply Φ exactly once (§2) and say so in a comment referencing this section.

## Appendix B — Spot-check audit list (AC-4.1b)

Run from repo root; expected results embedded. Last executed: see commit
AUDIT01/T4.1.

```
# 1. Exactly ONE definition of the closed-form engine under src/Packages:
grep -rn "^indexSetAnalyticCore\[" src/Packages/ | wc -l          # expect 1
# 2. No script-local copies resurrected:
grep -rn "indexSetAnalytic\[" --include="*.wl" --include="*.m" tests/ papers/method/code/ | \
  grep -v "IndexSetAnalytic\[" | wc -l                            # expect 0 (case-normalized callsites aside)
# 3. Phi appears only at documented boundaries:
grep -rn "FromDigits\[Reverse\[IntegerDigits" src/Packages/ src/integration/ tests/MUnit/Mixed/TSK-MIXED-001-FormulaVsExhaustiveTests.m | \
  grep -v "IndexAlgebra.m\|Gates.m\|allPosibleInputs\|setInputsToBinPhiStyle\|FormulaVsExhaustiveTests"
#    -> expect empty (each hit above is a declared boundary: Phi itself, its
#       private twin, the legacy LSB enumerators, and the mixed test's single
#       transport point)
# 4. Legacy guards present (six sites):
grep -rn "Failure\[\"UnsupportedGate\"" src/integration/Alpha.m | grep -v "^\s*[0-9]*:\s*\*" | wc -l
#    -> expect 7 hits: 6 guard assignments + 1 header-comment mention
# 5. CANALISING relative convention pinned:
ls tests/MUnit/Gates/TSK-GATES-014-CanalisingCoordTests.m         # exists; Status.txt OK under results/tests/gates014canalisingcoord/
```

Deviations from any expectation belong in Appendix D of AUDIT_FIXING_PLAN_01
before further action.
