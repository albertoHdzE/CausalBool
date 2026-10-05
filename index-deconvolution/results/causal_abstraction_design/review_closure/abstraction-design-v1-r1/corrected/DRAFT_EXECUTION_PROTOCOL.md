> **Corrected copy** (`review_closure/abstraction-design-v1-r1`, closing REVIEW R1–R3 and nonblocking notes). Original unchanged at `../../../abstraction-design-v1-r1/`. Changes: `../CHANGELOG.md`.

# DRAFT execution protocol — multilevel abstraction validation (corrected)

# **NOT AUTHORIZED FOR EXECUTION**

Draft for Codex review. Not implemented, not run, not scheduled. Execution requires a separate
written authorization naming this file and its sha256 at freeze.

## 1. Frozen declarations (from corrected `MODEL_AND_MAPS.md`)

Models M1–M4 (4; 1,792 states); T = {1,2,4,8,16}; family A: 135 (n=8), 141 (n=10), canonical ids
and D row ids 0–2,729 (§4); Track-D Q of size 5n+2 (42 / 52) in the declared order; β_fine
(singleton classes) plus hypotheses H-COARSE and H-OUT and the representative rule (§5);
Track-V controls P1–P4, N1–N3, C1–C2 (30,976 supplied pairs, 2,080 expected failures);
calibrations H-M1-τ (405 raw E2-consistent pairs), H-M2-F3 (75 of 150); X on all F3 pairs
(30·5·3 + 36·5 = 630), E2 only; fixtures FX-R1a/b/c and FX-REP. Any change after freeze voids the run.

## 2. Ownership and import identities

| concept | owner (path relative to CausalBool) | import |
|---|---|---|
| ECA ring network | `index-deconvolution/src/ca_deconvolution.py:heterogeneous_eca_network` | `ca_deconvolution` |
| `Network`, F tables, `essential_variables` (line 95) | `index-deconvolution/src/deconvolution.py`, `index-deconvolution/src/causalbool.py` | `deconvolution`, `causalbool` |
| knockout | `index-deconvolution/src/reprogramming.py:knockout` (line 71) | `reprogramming` |
| `.bnet` parsing | `index-deconvolution/src/bnet.py:parse_bnet` | `bnet` |
| fibre/abstraction checker | **prospective**: `index-deconvolution/src/deconvolution.py` (extend the core; thin study orchestration; no competing core) | ticket `../OWNERSHIP_TICKET.md`; must be accepted before code |
| gaps | `../series-deconvolution/src/seqdecon/operators.py:gaps` (line 133; read-only confirmed) | **U3 unresolved**: no declared import route into this repo |
| block-value occurrence sets | **U2 unresolved**: no extractor exists in the owner | ticket upstream required; not to be written locally |
| description length | deferred (no owned encoding for these maps); root `src/description_lengths.py` is a different source root and is not imported | — |

The modules import each other by bare name (`from causalbool import Network`, grep-confirmed), so
the route is `PYTHONPATH=index-deconvolution/src` (cwd = CausalBool) with bare imports. Root `src/`
holds none of these names (listing-confirmed) and is a different source root. Not executed here. The sibling `.pth` collision
(a foreign `hierarchy` module) must be checked at freeze by printing each imported module's
`__file__`.

## 3. Development, tests and freeze (before any production row)

1. Implement only after the ticket is accepted; tests first, on fixtures drawn from the declared
   models (no new model): FX-R1a/b/c (wrong β, R1 counterexample), FX-REP (failed representative,
   NOT-EVALUABLE reason stored, no invented mismatch count), an injected missing record (→
   INCOMPLETE; with an observed failure → NOT-FULL-INCOMPLETE), a ragged partition (P(3,1,8):
   blocks of length 1, 3, 3, 1), recoding theorem test (every F1 val G_q exists), the decision-table
   rows 1–7 each hit at least once, and counting controls (fixture counts equal §1; empty input
   refuses with exit 2 and prints its denominator).
2. **Freeze** before observing any D row: sha256 of this protocol, corrected `MODEL_AND_MAPS.md`
   and `DESIGN.md`, `fixtures.json` (models, partitions, ids, Q order, β schemes, controls), the
   audit selection list (§5), and every implementation source (core module, orchestrator, audit script).

## 4. Stages

1. Track V + calibrations + theorem tests + X. Any deviation → CHECKER-INVALID, stop; no D/G output.
2. Track D: rows in row-id order (model M1…M4, candidate id, τ). Every declared pair evaluated; no
   early exit; labels by DESIGN §5.1/§5.2 in reporting.
3. Track G (blocked until U2 and U3 close): after D is frozen; ranking never reads D; G1 joined after.
4. Report every row (render, not summary), raw and partition-grouped; descriptive count of FULL
   lossy M3/M4 candidates that are F3 vs non-F3 (no stop rule).

## 5. Validation and independent audit

- Exit non-zero on CHECKER-INVALID, count mismatch, or any unchecked declared pair.
- An independently written audit script recomputes Track V, N-control failing counts, H-M2-F3,
  H-M1-τ and the D rows with row id ≡ 0 (mod 10): rows 0, 10, …, 2,720 = **273 of 2,730**, exactly
  10 %. Comparison is canonical: sorted-key JSON of scientific fields only (ids, labels, counts,
  witnesses, Q′, class outcomes); wall time, RSS, timestamps and host are excluded.
- Preservation before/after of all inputs; notebook19/build_19 drift recorded, never reverted.

## 6. Proposed staged budget (proposal only; authorizes nothing)

The < 300 s compute figure is an **unmeasured estimate** (≈ 6·10^7 look-ups), not a feasibility
result. Proposed executor allowance: development and tests 900 s, freeze 60 s, run 600 s, audit
300 s, report and handoff 300 s = **2,160 s**, plus **300 s** supervisor reserve = 2,460 s. Stop
optional work at 80 %; overrun → INCOMPLETE with declared/checked denominators, never a partial pass.

## 7. Deliverables (of a future authorized run)

`fixtures.json`, `results_v.json`, `results_d.jsonl` (one row per row id), `results_x.json`,
`results_g.json` (or BLOCKED with U2/U3), `audit.json`, `REPORT.md`, ledgers, manifests, `HANDOFF.md`.

## 8. Design falsifier

If any Track-V or fixture hand derivation is wrong, the design (not the model) is at fault and must
be re-reviewed before any rerun. (The former majority-F3 stop rule is withdrawn: REVIEW R2.)
