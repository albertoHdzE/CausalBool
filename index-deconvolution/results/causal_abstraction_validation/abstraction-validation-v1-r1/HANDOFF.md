# HANDOFF — `abstraction-validation-v1-r1`

**Status: ready for Codex review; not yet accepted.**
V, D and X were executed under freeze. Track G is DEFERRED_DEPENDENCY (U2/U3) with zero G work, so the four-track
study is not complete. No commit, push, publication, schedule or recurring task. The sibling repository was not touched.

## Result in one paragraph
Every hand prediction held:
- V: 30,976 pairs and 2,080 failures, per control;
- H-M1-τ: 405 of 405;
- H-M2-F3: 75 of 150, all 150 pairs individually;
- theorem checks: 9,790 of 9,790;
- X: 630 of 630.

D evaluated all 2,730 rows and all 59,312,640 declared pairs. FULL lossy rows: 98 of the 2,510 non-control rows.
- M1: 0.
- M2: 45, all F3 low-bit blocks.
- M3: 8, all non-F3. They form one partition, the all-ones indicator, and every induced map is constant.
- M4: 45, of which 40 are F3 and 5 non-F3. Three non-F3 rows are the all-ones indicator, again with constant maps. Two are
  `F4 or∘or (4,1) o2=1` at τ 8 and 16, whose induced map G(z) = (z₀,z₀,z₀) is carried by the self-looped v000.

H-COARSE holds only on the 11 constant-map rows. H-OUT holds exactly on the 85 FULL F3 rows of M2 and M4. The
independent audit passed 18 of 18 checks, including all scientific fields of the 273 selected rows. Detail is in `REPORT.md`.

## Points for the reviewer
1. **Degenerate FULL.** 11 of the 13 non-F3 FULL rows in M3/M4 have constant induced maps. The design declared no
   non-triviality endpoint, so they keep their declared label. They are explicitly described as trivial and are not
   counted as evidence of informative macro dynamics. Whether to declare such an endpoint is a design question (`DECISION.md`).
2. **Guards.** `check_single_engine.sh` fails on `index-deconvolution/protocols/description_lengths.py`. That file was untracked
   and present before this run, as `logs/git_status_before.txt` and `preservation_before.json` show. It is not caused here
   and was not repaired. The test-manifest, glossary-conformance and import-safety guards pass. `make ci-local` was not run,
   because it can rewrite unrelated dirty artefacts. Scoped checks: ruff clean on all new and changed files;
   `test_deconvolution.py` 36 of 36; `test_abstraction.py` plus `test_study.py` 27 of 27; 6 of 6 mutants killed (`mutation_results.json`).
3. **Audit scope.** The 273 rows are deterministic coverage, not a sample. `beta_fine_all_singletons` is compared to a
   constant in the oracle. The oracle uses `bnet.parse_bnet` and `causalbool.repertoire` for M4 (disclosed).
4. **Fixture exposure before freeze.** The fixtures computed D evidence for (M2, F3 [0,4), 1), (M2, F1 val (4,0), 1) and
   (M1, F1 par (2,0), 2), as declared in `fixtures.json`. No other D result was inspected before freeze.
5. **Single-owner guard** is textual. It rejects a planted copy and does not prove semantic uniqueness.

## Integrity
- Inputs verified before work: corrected draft sha256 `876c4340…cb68`, and closure and supervision manifests (18 + 13 + 4 entries).
  See `input_verification.json`.
- Freeze `freeze.json`: 26 files, including imported owners. Import origins are all `index-deconvolution/src`, with no `.pth` collision.
  No frozen file changed after freeze. There was one attempt per production stage (`attempts.jsonl`).
- Core patch: `core_before/deconvolution.py.orig` and `core_patch.diff` (additive only).
- Preservation: 110,065 files under `index-deconvolution/` and `GOVERNANCE/`. Only the two permitted paths differ, the
  core file and the new `tests/test_abstraction.py` (`preservation_diff.json`).
- Manifest: `output_manifest.json`, with presentation-only files hashed separately.

## Time (executor, wall clock, continuous; see `time_ledger.jsonl`)
| category | allowance (s) | used (s) |
|---|---|---|
| development and tests | 900 | 771 |
| freeze | 60 | 7 |
| run | 600 | 29 |
| audit | 300 | 63 |
| reporting and handoff | 300 | 219 |

Total 1089 s of 2,160 s. The 300 s Codex reserve is untouched. Every category is within its allowance; nothing was transferred.
(An interim conservative estimate of 398 s for reporting was replaced by the measured interval.)

## Next action (for Codex)
Review this run. No further phase is started.
