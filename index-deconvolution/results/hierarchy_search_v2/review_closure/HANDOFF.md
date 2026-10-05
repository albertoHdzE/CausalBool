# HID-search-v2 review closure (R1, R2): handoff to the supervisor

Date: 2026-10-03. Developer/executor: Claude Code. Supervisor: Codex.
Kickoff: `index-deconvolution/KICKOFF_hierarchy_search_v2_closure.md` (sha256 `06086f3a…`,
equal to `supervision/closure_delegation_manifest.json`).
Run: **`search-confirm-v2-r1`**. Freeze, unchanged:
**`0f0a72ef2f9d9faac406b6d18594a45ba9dc71ff1d0331f38c6a3fead68e1d49`**.

Status: **ready for Codex review; not yet accepted.** Nothing was committed, pushed or
published. The scientific conclusion is still **inconclusive** and was not reopened.

## 1. Identity and starting state

- Git HEAD `53c41d8f3b97106fd176f24d575e0934848dddd6`, dirty tree. `baseline/git_status_before.txt`
  has 260 status lines, recorded before any edit.
- All eight review-baseline hashes in `closure_delegation_manifest.json` and the kickoff
  hash matched before work. 62 of 62 freeze-named source, protocol and informational
  files matched the freeze (`baseline/preservation_before.json`).
- Execution ledger before this assignment: diagnostics/verification 2,174.6 / 7,200 s;
  total 14,678.9 / 43,200 s (3,544 entries). This matches the supervisor's figures.
- Graph tools: the codebase-memory MCP tools were not used. Discovery was by grep over
  the owners named in REVIEW.md, which was sufficient for a two-file correction. No
  AGENTS.md applies here; the only one in the repository is under `luminal-challenge/`.

## 2. Isolated copy

`/tmp/hid_review_closure_20261003/` (outside the repository):

| Copy | Purpose | Identity |
|---|---|---|
| `CausalBool/` | patched | local git, baseline commit `4c8d905` = working-tree bytes of `hierarchy/` and `build_17.py` |
| `baseline/` | pristine control | same bytes, unpatched |
| `mutation_probe/` | defect-detection probe | patched copy with only the median expression reverted |

Each copy holds rsync'd working-tree bytes (not a HEAD checkout) of `src/`,
`index-deconvolution/{hierarchy,src,notebooks,experiments,protocols}`, the top-level
`index-deconvolution` files, `imp-causalNet-paper/src`, the root `conftest.py`,
`pytest.ini` and `ruff.toml`, `tests/MUnit/MANIFEST.tsv`, and
`tests/analysis/test_description_lengths_values.py`. `venv` and
`index-deconvolution/results/{hierarchy_search_v2,hierarchy_v1}` are **symlinks** to
the repository and are used read-only. The preservation proof in §7 shows nothing was
written through them.

| File | Baseline sha256 | Patched sha256 |
|---|---|---|
| `index-deconvolution/hierarchy/diagnostics_v2.py` | `a73d0650966a5528ed10383e4948cfa16d23a62171f1f4557be6964d0ba7e2c7` (= freeze) | `a89e95852549d9b26cd286fea97ec687f3703e59b0306d4f8383b838080e7545` |
| `index-deconvolution/hierarchy/tests/test_study_v2.py` | `17b2e73363da61956b2061fbf3164bac794490730685a01ef3d195c53cb6e986` | `61c9edf48fac432008aa25b928ab4934b6a81e50f8ebc621533f6db8f8eed34a` |
| `index-deconvolution/notebooks/build_17.py` | `612daf748dfeff1236d1f6c08ce182f931ecd9633a20fb3739f8d23ded928ec0` | `91ac327cf7605b8ee13cbe6595549660fa29c2b4e4de0aa27ceccdcab431a420` |
| `index-deconvolution/notebooks/17_hierarchy_search_v2.ipynb` (built, unexecuted) | `8bebb75e…` (original, executed) | `01b5ca86fb95e0785ad9bc44c4eff5830e510bc0977fa4b27bd0c5bf5de0976b` |

## 3. R1 — diagnostic median erratum and owner repair

**Erratum.** `diagnostic_median_erratum.json` and `DIAGNOSTIC_MEDIAN_ERRATUM.md`. The
erratum was derived read-only from the retained `references.json` (sha256 `937940b6…`)
and the saved archives. For all 176 of 176 records, the checks on archive hash, length,
decoding to the case's recorded input hash, row bits, raw bits and exact gap
recomputation pass. All eight cells were compared, not only the five reported:

| Cell | n | Stored | Corrected |
|---|---:|---:|---:|
| confirmation F12 256 / 1,024 / 4,096 | 40 each | 0.0 / −0.062317429406037 / 0.076171875 | unchanged (middle values coincide) |
| transfer F12 16,384 | 8 | 0.1196070055531824 | 0.1181531121515912 |
| transfer F12 65,536 | 8 | 0.09033203125 | 0.09032996380852432 |
| transfer F12 131,072 | 8 | 0.0834941827198169 | 0.08346462065678345 |
| stress S02 4,096 | 16 | −0.021484375 | −0.022452360712978778 |
| stress S02 65,536 | 16 | 0.008422466012603182 | 0.004455362455942263 |

Units are bits per input bit. The five corrections reproduce `supervision/diagnostic_audit.json`
exactly. The derivation enforces this agreement and exits non-zero on any disagreement.
Membership, counts, means, signs and shorter/longer/tie tallies are exactly unchanged.
The derivation exited 0 (`logs/derive_median_erratum.log`). Script sha256 `903ffa55…`;
the erratum embeds it together with the input hashes and the hash of every imported module.

**Owner repair** (`R1_diagnostics_median_repair.patch`, sha256
`e8da5c6ba731d4635295e867e04d3fe4d303adad42ffebeed18d744be1de96c5`, 148 lines). The
cell aggregation inside `boundary_references` moves into
`diagnostics_v2.boundary_gap_summary(items)` in the same owner, and `gap_median`
becomes `statistics.median(g)`. `boundary_references` calls it, so there is still one
production implementation. The erratum's corrected values come from this function, run
on the saved records.

Four tests go through that owner, appended to `test_study_v2.py` §11:

1. An even, mixed-sign cell: median 0.05, where the old code reported the upper middle 0.2.
2. An odd cell, with a second even negative cell kept separate.
3. Unavailable records and an empty cell, where the median and mean stay `None`.
4. A wiring check through the production CLI on the fixture study.

**Defect detection, measured.** Reinstating only `g[len(g) // 2]` in `mutation_probe/`
makes tests 1 and 2 fail and tests 3 and 4 pass (`logs/mutation_probe_upper_middle.log`).
Test 4 does not catch the defect on the fixture data, because in every fixture cell the
two middle gaps coincide. Its comment says so. The defect is caught by tests 1 and 2.

This patch is a **separately identified repair** for later integration. It does not
match the original freeze and makes no claim to. Under PROTOCOL §6, adopting it into a
frozen study needs the amendment/new-identity route. It was not applied to the repository.

## 4. R2 — notebook 17 reads saved artefacts only

**Builder** (`R2_build_17_artifact_only.patch`, sha256
`37dc7f1f20a414a19de4a06ea51e82f881dd699f0a1252a2f14fec13ccc4d855`, 214 lines):

- `from hierarchy.search_v2 import ARMS, infer_v2` and the `random`-built period-63 input
  are removed. No encoder, search or corpus module is imported. The arm order comes from
  each arm's saved `stages_included`, with an assertion that the stage counts run 1 to 6.
- §3 now uses the explicit retained case **`confirmation-F06-1024-3000-base`**. It is
  selected by rule: the first declared replicate, the base string, the middle size, and
  F06, the family on which P, C, D and G are read. It is labelled as an illustration,
  not an endpoint. For each of the six arms the saved archive is hash- and length-checked
  against its row, decoded and matched to the recorded input hash. Stages, per-stage
  incumbents, the field-cost buckets of `hid_global` and its parsed rules come from
  saved telemetry and archive bytes, using the existing `decode`/`ledger` owners.
- §10 reads `review_closure/diagnostic_median_erratum.json`. It refuses unless the
  erratum's run, freeze and input hashes match the current files. It shows the
  corrected median, with each corrected one tagged `CORRECTED (stored …)`, and asserts
  that every unchanged quantity equals `diagnostics.json`.
- §11 states whether the run's `verification.json` is byte-identical to
  `supervision/verification_full.json`; it is (sha256 `74bed6ff…`). The record's
  "notebook 17" line refers to the earlier revision, and the prose says so.
- Artefact root: SETUP resolves `ID_ROOT` explicitly from the working directory or
  `index-deconvolution/`, asserts that the artefacts exist, and prints the root.
- The primary, contrast, descriptive, resource, cost and limitation cells are unchanged.

**Execution** (`scripts/execute_notebook_artifact_only.py`, sha256 `5cc14ef9…`). This is
a harness only, and no production code is touched. An IPython startup file in a private
`IPYTHONDIR` puts two guards inside the kernel:

- An import gate. Only `hierarchy`, `.decode`, `.ledger`, `.codes` and `.model` are
  allowed, and nothing may load from `index-deconvolution/src`.
- An audit hook. It refuses writes below either `results/` root (symlinks resolved) and
  refuses any subprocess.

Results (`notebook_execution_checks.json`, all ten checks true; `logs/notebook_execution.log`, exit 0):

- Executed from the notebook directory and from the repository root: 15 code cells,
  0 error outputs, 0 unexecuted. The guard log is present and records zero refusals.
  The imported hierarchy modules are exactly the five allowlisted ones, from the
  isolated copy.
- The text outputs of the two runs are identical except cell 0. That cell is the shared
  `_nblib` BOOTSTRAP banner: from the repository root it falls back to the installed
  checkout path, and SETUP then re-roots explicitly. `_nblib.py` is not owned here.
- The displayed medians come from the erratum (8 of 8 lines checked, labels match
  `changed`). The primary estimate `0.005605234982532739`, its CI, the verdict
  `inconclusive` and all five contrast lines print with their saved values.
- 10 code cells have the same source as the original notebook. 9 have identical text
  outputs; the only difference is the bootstrap banner path.
- **Negative control:** the same harness on the original notebook in `baseline/` is
  refused at SETUP (`ImportError: … hierarchy.search_v2 refused`), exit 1, in both working
  directories (`notebook_execution_checks.negative_control.json`).

Deliverable: `17_hierarchy_search_v2.corrected.ipynb` (sha256 `ed5ff3fc…`), executed from
the notebook directory. The original `notebooks/17_hierarchy_search_v2.ipynb` and its
outputs are unchanged, for comparison.

## 5. Tests and lint

All runs below were in the isolated copies, using the retained command
`venv/bin/python -m pytest index-deconvolution/hierarchy/tests tests/analysis/test_description_lengths_values.py -q --tb=short -p no:cacheprovider`:

| Run | Result | Log |
|---|---|---|
| Pristine baseline copy | **385 passed**, exit 0 (85 s) | `logs/pytest_isolated_baseline.log` |
| Patched copy | **389 passed**, exit 0 (86 s) | `logs/pytest_isolated_patched.log` |
| Collection diff | +4, −0: exactly the four §11 tests | `logs/collect_isolated_{baseline,patched}.txt` |
| ruff, retained V2 lint set, patched copy | `All checks passed!`, exit 0 | `logs/ruff_isolated_patched.log` |
| ruff, correction scripts | clean | — |

Three earlier runs were discarded, and the reasons are disclosed:

- One run was started before the patch but imported the lazily-loaded owner after it.
- Two runs used an incomplete mirror. The missing HID-v1 protocol files and
  `imp-causalNet-paper/src` caused 39 errors and 4 failures, none of them code defects.

The mirror was completed and both suites were rerun from the start.

Not rerun: `verify` and `report` against the original run, because they write into it.
The supervisor's retained `verify --full` stands for the original sources. The
repository guards and `make ci-local` were not run, for the reasons in REVIEW.md. The
pre-existing single-engine failure remains a failure.

## 6. What Codex would integrate

1. `git apply R1_diagnostics_median_repair.patch`. This is a source change under a new
   identity or amendment, per PROTOCOL §6, and must not be applied under the existing
   freeze. `git apply --check` against the live tree passes.
2. `git apply R2_build_17_artifact_only.patch`, then replace
   `notebooks/17_hierarchy_search_v2.ipynb` with the executed corrected notebook, or
   rebuild and re-execute it. The builder reads the erratum at
   `results/hierarchy_search_v2/review_closure/diagnostic_median_erratum.json`, so that
   path must stay, or the builder constant must be updated with it.
   `git apply --check` passes.
3. Optionally, append this assignment's time to `execution_ledger.jsonl` (see §8). I did
   not write to the ledger because it is a protected study file.

Everything else stays isolated: the `/tmp` copies, the probe, and the harness's
temporary `IPYTHONDIR`.

## 7. Preservation proof

`scripts/preservation_check.py` (sha256 `65c3a7d6…`) reuses the existing owner
`experiments/preserve_confirm_v1_r1_sources.tree_hash`. `after` exited 0 with zero
differences (`baseline/preservation_after.json`) across:

- 9 trees: `confirm-v1` 18,058 files and `confirm-v1-r1` 18,062 files, both with the
  same aggregates as in REVIEW (`8aa2326e…`, `46c84ce8…`); the whole of
  `search-confirm-v2-r1`; `development`, `prefreeze`, `preservation` and `supervision`;
  the `hierarchy/` package; and `protocols/hierarchy_search_v2`.
- 12 files: notebooks 16 and 17, both builders, `_nblib`, the protocol, the kickoff,
  the execution ledger, the development attempts, the implementation map and two
  experiment scripts.
- 62 of 62 freeze-named files.
- 93 unrelated tracked edits.

`git status` before and after differ only in `review_closure/` paths.

## 8. Resource accounting

The assignment ran from 16:35:30 UTC. At 16:48:31 UTC the measured wall-clock time was
781 s. I charge a conservative **1,200 s** to cover writing this handoff. The work was
sequential test and notebook jobs, with no encoding, no benchmark workers and no
concurrent study. Charged to diagnostics/verification:

- this assignment: 1,200 s;
- cumulative for diagnostics/verification: 2,174.6 + 1,200 = **3,374.6 / 7,200 s**;
- cumulative overall: 14,678.9 + 1,200 = **15,878.9 / 43,200 s**.

The prior study time was not reset and the ledger was not modified.

## 9. Changed-file inventory and unresolved items

**New, inside `review_closure/` only:** `HANDOFF.md`, `DIAGNOSTIC_MEDIAN_ERRATUM.md`,
`diagnostic_median_erratum.json`, both patches, the corrected notebook and its
negative-control notebook, both execution-check JSONs, `scripts/` (three scripts),
`baseline/` (status and preservation before/after), and `logs/` (10 files). No other
file in the repository was created or modified.

Open for decision:

- **(a) R1 identity.** Does the R1 repair go in as a protocol amendment with a new
  source identity, or wait for the next study?
- **(b) Bootstrap fallback.** `_nblib.BOOTSTRAP` silently falls back to the installed
  checkout. SETUP now corrects this for notebook 17, but other notebooks inherit the
  behaviour. That is outside this assignment's ownership.
- **(c) HID-v1 quantiles, observation only.** `hierarchy/diagnostics.py:158`
  (`_quantiles`) reports nearest-rank order statistics for HID-v1 null scores, including
  `s[n // 2]`. They are labelled as quantiles, not medians, and belong to the frozen
  historical package. They were not examined further or changed.

Ready for Codex review; not yet accepted.
