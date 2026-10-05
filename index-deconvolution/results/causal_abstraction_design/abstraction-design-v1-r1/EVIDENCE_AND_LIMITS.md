# Evidence and limits — `abstraction-design-v1-r1`

## 1. Local evidence used (hashes in `input_manifest.json`)

| source | section inspected | used for |
|---|---|---|
| accepted closure `REVIEW.md`, `NEXT_CLAUDE.md` | whole | scope, interpretation notes (codomain, one-step, controls) |
| corrected `ABSTRACTION_CONTRACT.md` §1–§5, `EVALUATION_SPEC.md` §1–§3, `TARGET_CONTRACT.md` §1–§2, `DRAFT_WITHDRAWAL_ERRATUM.md` (head) | as listed | definitions, (iv-a)/(iv-b), denominators, intervention timing |
| `witnesses.json` (W1–W2 bodies, W3 header) | W1, W2 | conventions only; W3/W4 are not re-used as the question |
| `src/ca_deconvolution.py` lines 37–111 | `eca_next_cell`, `heterogeneous_eca_network` | M1, M3 owner and rule-index convention |
| `src/deconvolution.py` (grep) | bit order note line 34, `essential_variables` line 95 | encoding, Track X |
| `src/reprogramming.py` (grep) | `knockout` line 71 | mechanism-replacement owner |
| `src/bnet.py` (grep), `egfr_signaling.bnet`, `lambda_phage.bnet`, `lac_operon.bnet` (size only) | — | M4 choice; lac_operon reserved as untouched hold-out |
| `hierarchy/candidates.py`, `diagnostics_v2.py` (grep) | `positions_of`, `ap_runs`, boundary gaps | gap/occurrence owners |
| `GOVERNANCE/GLOSSARY.md` §5 | occurrence set, gaps | Track G definitions; owner `operators.py` lives in the sibling `series-deconvolution` repository |

Nothing was executed except hashing and JSON checks. No code, simulator, map search or notebook.

## 2. Literature and novelty

| reference | status in this phase | relation |
|---|---|---|
| Rubenstein et al. 2017 (Def. 1, 3, Thm 6); Beckers & Halpern 2019 (Def. 3.1–3.15) | read in the earlier phase (closure manifest); not re-read | the intervention-consistency criterion; our dynamical transfer is a construction (contract header) |
| Israeli & Goldenfeld, *Phys. Rev. E* 73, 026203 (2006), arXiv:nlin/0508033; PRL 92, 074105 (2004) | **search-result summary only** (2026-10-05); PDF not read | coarse-graining of ECA by supercell projection with α∘F^N = F̄∘α; rule 150 reported as a fixed point of coarse-graining — P1 is a finite-ring instance of a known result |
| Song & Grochow, arXiv:2012.12153 | **search-result summary only** | exhaustive search of ECA coarse-grainings up to supercell 7: autonomous block-map abstractions of homogeneous CA (M1, M3) are a searched problem |
| Kemeny & Snell (lumpability); Lind & Marcus (factor maps / semi-conjugacy); Naldi et al. 2011 (dynamically consistent reduction of logical regulatory graphs) | **cited from memory, UNVERIFIED** | the autonomous condition is classical; M4-style reduction has prior art |

**Novelty claim: none.** The design is a carefully labelled validation of a known criterion
(commuting square plus τ-abstraction-style intervention consistency) on a declared finite
family. What is not, to our knowledge, covered by the two search-verified CA papers is the
joint intervention test with structural β hold-out on finite rings; this is **unverified**
against Beckers–Halpern follow-ups and the CA literature and must not be claimed as new.

## 3. Limits

1. Four models, n ≤ 10, one hand-free nonlinear CA and one biological model: every D result is
   an existence statement about family A on these models.
2. Block maps on M4 act on an arbitrary file order of nodes; results describe that encoding,
   not biology.
3. M1 is degenerate at τ ≥ 4 (F⁴ = 1); half of M1's τ grid tests nothing but the controls.
4. Level-2 nesting is analyst-imposed; on n ≤ 10 one non-degenerate level only.
5. Track G sees only 6 trajectories of 64 steps; M2 high-bit gaps (period 256) are not observed.
6. Interventions inside a macro step, macro interventions without micro counterparts, and
   interventions outside Q are untested.
7. Literature rows marked search-only or unverified have not been read in primary form.
8. Description lengths are reported but are not a criterion; no compression result is in scope.
