# 44 · bdm_anatomy_v1: what the frozen protocol found

**Date:** 2026-10-04. **Protocol:** `protocols/bdm_anatomy_v1/PROTOCOL.md` (v1.0, Amendments
1 and 2). **Run of record:** `results/bdm_anatomy_v1/a3` (MANIFEST verified). **Notebook:**
`notebooks/19_bdm_and_index_complexity.ipynb` (built by `build_19.py`; reads `a3`, checks the
hashes, re-computes one saved record of every hypothesis live). **Plan:**
`plans/wait-we-can-do-floating-starlight.md`.

## Run history

| run | status | why |
|---|---|---|
| `a1` | stopped in H1 | the owner's trace check used an absolute 1e-9 tolerance on a 100,000-term sum (relative error 2e-12). Amendment 1: relative tolerance; no value changes. DM, T1, T2 files kept, unused. |
| `a2` | complete | DM3 was broken: the producer drew each character of DM3 strings from a fresh generator, so they were constant. Found while checking notebook prose against output. |
| `a3` | **of record** | Amendment 2 fixed DM3 only. All eight hypothesis files are byte-identical to `a2` (asserted in the notebook). |

## Verdicts (pre-registered rules)

| id | verdict | the number that decided it |
|---|---|---|
| T1 permutation invariance | supported | 0 failures / 42,000 |
| T2 log bound | supported | 0 violations / 75 |
| H1 BDM per bit drifts; complete code does not | supported | BDM/N 2.67 → 0.127 over N = 1.2e3 → 1.2e6 (20 seeds each); decodable/N ends at 1.13 |
| H2 fill ratio predicts seam visibility | **not supported** | leave-one-out AUC 0.63 (needed 0.90); 40/49 cells visible |
| H3 single-cell signs depend on the grid | **not supported** | mean instability 0.107, CI 0.093–0.122 (needed > 0.10); 80/256 rules above 0.10; Spearman with randomness 0.86 |
| H4 groups survive, single cells do not | supported | median group agreement 1.00; median single-cell rank agreement 0.24 |
| H5 simple methods emulate BDM | regime map | E1/E2 in 5/23 regimes (block 4 from 96 bits; block 8 at 6,144); E0, zlib, lzma, HID in 0/23 |
| H6 certified code vs BDM | descriptive | BDM > certified in 5,120/5,120 diagrams; median ratio ≈ 6 at every run length |
| H7 two-rule boundaries | **no valid baseline** | A0: ours 0.83, BDM 0.40 (needed both ≥ 0.90) |

## What changed in the owners

- `src/description_lengths.py`: `block_code_parts` (dictionary / counts / arrangement +
  decodable prefix-code length), `certified_eca_code`; relative tolerance in the two internal
  consistency checks.
- `index-deconvolution/src/ca_deconvolution.py`: `heterogeneous_eca_network`.
- `tests/analysis/test_bdm_anatomy_owner.py` (274 tests incl. round-trip encoders/decoders),
  declared in the manifest (122 files); `tools/check_single_engine.sh` guards the two new
  owners (verified red on a planted copy); `GOVERNANCE/DESCRIPTION_LENGTHS.md` §1d.
- Erratum in `imp-causalNet-paper/.../measure.py`: `two_part_code` priced the seed with BDM, so
  it is not a certificate; kept unchanged under its own name because published replication
  numbers depend on it.

## Errata to bitacora 43

Listed in notebook 19 §11. In short: the fill-ratio law, the emulation statement, the
"any object / noisy data are BDM-only" rows, the reading of C3 (a period that misses the grid
fools BDM only when the string is short relative to lcm(period, block)), and the scale of C5.

## Open

A properly specified BDM boundary estimator for H7; the cause of the nine hidden H2 cells;
the same anatomy on four-letter strings with known generators.

## Note on the pre-existing guard state

`tools/check_single_engine.sh` was already red before this work, from `.kilo/worktrees/*`
copies and `index-deconvolution/protocols/description_lengths.py`. Not touched here.
