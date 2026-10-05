# DRAFT execution protocol — multilevel abstraction validation

# **NOT AUTHORIZED FOR EXECUTION**

Draft for Codex review. Not implemented, not run, not scheduled. Execution requires a separate
written authorization naming this file and its sha256 at freeze.

## 1. Frozen declarations (from `MODEL_AND_MAPS.md`)

Models M1–M4 (4; 1,792 states); T = {1,2,4,8,16}; family A: 135 maps (n=8), 141 (n=10);
2,730 (α, τ) pairs; Track-D Q of size 5n+2 (42 / 52) in the declared order; structural β and
representative rule (§5); Track-V controls P1–P4, N1–N3, C1–C2 (30,976 supplied pairs, 2,080
expected failures); calibrations H-M1-τ (405 raw consistent pairs), H-M2-F3 (75 of 150);
cross-check X on all F3 pairs (30·5·3 + 36·5 = 630). Any change after freeze voids the run.

## 2. Ownership (monolithic-code Q1–Q4, to be answered again at implementation)

| concept | owner | rule |
|---|---|---|
| ECA ring network | `src/ca_deconvolution.py:heterogeneous_eca_network` | import; no copy |
| `Network`, F tables, `essential_variables` | `src/deconvolution.py`, `src/causalbool.py` | import |
| knockout | `src/reprogramming.py:knockout` | import |
| `.bnet` parsing | `src/bnet.py:parse_bnet` | import |
| fibre/abstraction checker | **no owner exists** (the earlier `check_witnesses.py` is a run-local witness script, not a core) | must be added to one declared core module with its guard; ticket before code |
| occurrence sets, gaps | sibling `series-deconvolution/operators.py` per GLOSSARY §5 | import or raise a ticket upstream; no local re-implementation |
| description length | `src/description_lengths.py` | import |

Run with `PYTHONPATH=index-deconvolution:src` (a sibling `.pth` ships a colliding module name).

## 3. Stages, ordering and stopping

1. **Freeze**: hash this protocol, `MODEL_AND_MAPS.md`, fixtures (a JSON listing every model
   formula, partition, candidate id in canonical order, Q order, β rule, supplied controls).
   Fixture counts must equal §1 by assertion; empty inputs refuse with exit 2.
2. **Track V + calibrations + X.** Any deviation from a hand prediction → CHECKER-INVALID, stop;
   report the deviation; no D/G output is produced.
3. **Track D**, models in order M1, M2, M3, M4; within a model τ ascending, candidates in
   canonical order (F1 by w, o, g in the order val, par, cnt, or, and; F2; F3 by w, o, block;
   F4; C). Every declared pair is evaluated; no early exit per candidate (failure precedence is
   applied in reporting, not by skipping).
4. **Track G** after D is complete and frozen (ranking cannot see D results while computed;
   G1 is computed by joining afterwards).
5. **Report** with every per-candidate row (render, not summary), both raw and partition-grouped.

Ties: rank ties broken by canonical order; ambiguity reports all members.

## 4. Budget

Executor ≤ 1,800 s wall including writing; compute expected under 300 s (≈ 6·10^7 table
look-ups with precomputed F^τ and F_q arrays). Stop optional work at 80 % of budget. Peak RSS
reported. Overrun → INCOMPLETE with the declared/checked denominators, never a partial pass.

## 5. Validation and independent audit

- Exit non-zero on any CHECKER-INVALID, count mismatch or unchecked declared pair.
- A second, independently written audit script recomputes Track V, N-control failing counts,
  H-M2-F3, H-M1-τ and 10 % of D rows chosen by the rule "every candidate id ≡ 0 mod 10 in
  canonical order" and compares bytewise.
- Preservation before/after of all inputs; notebook19/build19 drift recorded, never reverted.

## 6. Deliverables (of a future authorized run)

`fixtures.json`, `results_v.json`, `results_d.jsonl` (one row per (model, α, τ)),
`results_x.json`, `results_g.json`, `audit.json`, `REPORT.md`, ledgers, manifests, `HANDOFF.md`.

## 7. Falsifiers of the design itself

- If more than half of all nontrivial lossy FULL candidates in M3/M4 are F3 projections that X
  explains, the D question reduces to dependency-graph analysis; report so.
- If any Track-V hand derivation is wrong, the design (not the model) is at fault and must be
  re-reviewed before any rerun.
