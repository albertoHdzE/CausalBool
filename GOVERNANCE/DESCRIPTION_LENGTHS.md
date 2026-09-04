# DESCRIPTION_LENGTHS — Consolidated interface for description-length variants

**Status:** ACTIVE · Established by **AUDIT_FIXING_PLAN_01 / T4.5** (2026-08-25).
**Motivation (V5 stamp, Appendix F):** the four cost models in use are
*structurally distinct quantities that share one name*. On V5's shared toy node
(n=4 space, single AND node of degree 2) they evaluate to different bit counts —
nonidentity confirmed by execution; this document names them, scopes them, and
pins their parity fixtures so "D" is never silently ambiguous again.

## §1 The variants

| ID | Name | Cost model | Domain | Canonical implementation |
|---|---|---|---|---|
| **A** | row-run index-set length | per-row run-count × log₂(n+1) units + log₂(n+1) header | adjacency matrices (graphs as index-set tables) | `imp-causalNet-paper .../causalbool_mirror.index_set_description_length`; wrapper `row_run_index_set_length` |
| **B** | gate + index-set network cost | Σ_v [log₂ 12 + log₂ C(n,dᵥ) + gate term] (+ optional log₂ n header) | Boolean networks / molecular graphs with gate assignment | `imp-pathinfo-paper .../node_description_cost` & `graph_description_length`; WL twin `BioMetrics.m encodeNodeCost`; wrapper `graph_gate_index_length` |
| **C** | mechanism DNF model cost | essential-variable reduced DNF over a 3-valued cell alphabet | single rules/truth tables (two-part code mechanism term) | `imp-causalNet-paper .../measure.model_description_length`; wrapper `model_dnf_bits` |
| **D** | BioMetrics D | = B without the log₂ n header (V2 removed topology cost) | WL networks (`ComputeDescriptionLength[cm,dyn,params]`) | `src/Packages/Integration/BioMetrics.m` |
| **E** | schema normal form `D_schema` | γ(\|S\|+1) + Σ_s [log₂(n+1) + log₂ C(n,k_s) + k_s] over a node's schemata | Boolean nodes; **primary mechanism-side measure since AUDIT03/R3** | `src/description_lengths.schema_normal_form_length` (reuses `minimal_dnf`) |

### §1a The in-degree field (AUDIT03/R2b, 2026-09-04)

Variants B and D charge `log₂(n+1)` for the in-degree `d`. **Without it these are
not description lengths at all**: a decoder cannot know how many bits to read for
the input set, nor read them as an index into the `d`-subsets of `[n]`, so the
per-node code has Kraft sum `n+1` rather than 1. Proof and both negative
controls: `audit/AUDIT03_R3_description_length/verify_description_length.py`.

Eight sites carried this cost model and **four omitted the field**. They are now
collapsed:

| was | now |
|---|---|
| `tests/MUnit/Theory/TSK-THEORY-002-Tests.m` (no field) | delegates to `Integration\`BioMetrics\`` |
| `tests/MUnit/Theory/TSK-THEORY-004-Tests.m` (no field) | delegates to `Integration\`BioMetrics\`` |
| `tests/MUnit/Mixed/TSK-MIXED-001-FormulaVsExhaustiveTests.m` (had field, **dead code — never called**) | delegates to `Integration\`BioMetrics\`` |
| `src/description_lengths.py` (no field) | **owner**, field added, default `in_degree_field=True` |
| `papers/method/code/complexity_analysis/complexity_analysis.py` (had field) | keeps `D_formula`; `D_schema` delegates to the owner |
| `src/integration/bio_D_experiment.py`, `BioMetrics.m` | fixed at R3.1 |
| `imp-pathinfo-paper/.../causalbool_mirror.py` (no field) | **documented exception, pinned** — see §4a |

Declared deltas: `TSK-THEORY-002` `D` 42.4413 → 55.3662 (`5·log₂6`);
`TSK-THEORY-004` 28.509775 → 37.797487 (`4·log₂5`, now **identical to
`TSK-BIO-METRICS-001`**, which is the cross-check that the collapse worked).
Both tests assert *inequalities*, so no verdict moved. `TSK-MIXED-001`'s
`D_formula` is unchanged at `135.66005207461194` — it is the control: a correct
copy replaced by the owner must not move.

### §4a The pinned exception

`imp-pathinfo-paper`'s mirror omits the in-degree field and its **published
tables depend on that**, so it is not silently corrected. Both values are pinned
in the T4.5 fixture (`B_gate_plus_index_set_bits` and
`B_legacy_pathinfo_no_indegree_bits`) and the parity gate asserts their
difference is exactly `n·log₂(n+1)`. The owner reaches the legacy value through
`in_degree_field=False`, which is a legacy switch and **not** a modelling choice.

**The header asymmetry (V5):** pathinfo's graph-level value charges an extra
log₂(n) header that BioMetrics' D does not. On the T4.5 toy network the delta is
exactly log₂(4) = 2 bits — pinned by the parity fixture. Cross-repo claims
involving "D" must state which variant they mean.

## §2 Pinned toy fixture (executed 2026-08-25)

Fixture: `results/description_lengths/toy_fixture.json`, produced by
`tools/t45_description_length_fixtures.py` (n=4; AND node ← {1,2}; OR ← {3};
XOR ← {4}... see file for exact wiring). Executed values:

| Variant | Bits (full toy network) | superseded value |
|---|---|---|
| A row-run | 20.89735285398626 | — |
| B gate+index-set (header incl.) | **37.212524883155226** | 27.92481250360578 |
| B legacy, imp-pathinfo, no in-degree field | 27.92481250360578 | pinned, see §4a |
| C model-DNF (AND node table) | 6.339850002884624 | — |
| D BioMetrics D (WL) | **35.212524883155226** | 25.92481250360578 |
| E schema normal form | 34.8726748802706 | new at R2b |

The header asymmetry is preserved exactly: `B − D = 2 = log₂4`. The legacy gap
is `B − B_legacy = 9.2877 = 4·log₂5`.

**The parity gate was inert on the Wolfram arm and is now not.** It compared two
*stored* numbers (fixture `B` minus fixture `D`), so when R3.1 changed
`BioMetrics.m` the producer moved from 25.9248 to 35.2125 bits **while the gate
kept reporting OK**. It now executes `tools/t45_biometrics_toy.m` and compares.
Verified by planting the stale value: the gate fails with `WOLFRAM DRIFT`.

V5-stamp single-node values reproduced **elementwise** by the parity test:
AND-in-n=4 node cost = 7.169925001442312 (variant-B family, no header);
model-DNF = 6.339850002884624 (= C above); row-run on the single-band object =
3·log₂5 = 6.965784284662087 (= A's unit arithmetic).

Parity gate: `python tools/test_description_length_parity.py` → exit 0 required.
It re-computes every fixture value through the wrapper and asserts the V5 stamps
and the header delta.

## §3 The one wrapper

`src/description_lengths.py` is the supported Python entry point:

- pins `pybdm == 0.1.0` (hard check on import of the BDM path);
- exposes A/B/C plus `bdm_2d` with **explicit edge semantics**: `below_floor`
  ∈ {"none", "pathinfo", "raise"} — imp-pathinfo's historical None-below-4-atoms
  behaviour is preserved *per-consumer via the flag*, never silently;
- B carries `include_header=` to move between pathinfo-style (header) and
  BioMetrics-style (no header) values explicitly.

## §4 Consumers (import or documented exception)

| Consumer | Status |
|---|---|
| `tools/test_description_length_parity.py` | imports the wrapper (reference consumer) |
| `imp-causalNet-paper` (variants A, C) | **documented exception**: standalone venv + vendored root-module loading; mirror functions byte-frozen by its own suite (47 passed). Migration to the wrapper deferred to that subproject's own task. |
| `imp-pathinfo-paper` (variant B family) | **documented exception**: same rationale (own venv, 41 passed). |
| Wolfram side (variant D) | stays in `BioMetrics.m`; pinned by the fixture values above and re-verifiable via `tools/t45_biometrics_toy.m`. |

## §5 Rule going forward

Any new description-length claim must (a) name the variant by its §1 ID,
(b) trace numbers to a committed executed artifact, (c) route Python-side
computation through the wrapper or extend §4's exception table with a reason and
an owning task.
