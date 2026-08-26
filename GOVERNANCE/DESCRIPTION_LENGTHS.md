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

**The header asymmetry (V5):** pathinfo's graph-level value charges an extra
log₂(n) header that BioMetrics' D does not. On the T4.5 toy network the delta is
exactly log₂(4) = 2 bits — pinned by the parity fixture. Cross-repo claims
involving "D" must state which variant they mean.

## §2 Pinned toy fixture (executed 2026-08-25)

Fixture: `results/description_lengths/toy_fixture.json`, produced by
`tools/t45_description_length_fixtures.py` (n=4; AND node ← {1,2}; OR ← {3};
XOR ← {4}... see file for exact wiring). Executed values:

| Variant | Bits (full toy network) |
|---|---|
| A row-run | 20.89735285398626 |
| B gate+index-set (header incl.) | 27.92481250360578 |
| C model-DNF (AND node table) | 6.339850002884624 |
| D BioMetrics D (WL) | 25.92481250360578 |

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
