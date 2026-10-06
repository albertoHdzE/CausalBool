# Decision

**V1_READY_FOR_SUPERVISOR.** Every new scoped gate in ACCEPTANCE.md passed (see
HANDOFF.md). NO_NEW_STUDY_JUSTIFIED stands.

The decision covers the **exact known-model state-compaction v1 component** only:

- a tested owner (`minimal_task_partition`, `distinguishing_task_word`,
  `task_word_path`) under the explicit all-start, explicit-table contract;
- its documentation;
- its validated small-model evidence package.

It does not establish a general causal-deconvolution theory. It makes no claim of causal
discovery, archive-bit compression, scalability, fractal structure or novelty. Final
acceptance remains with the supervisor.

Inherited repository failures are not resolved and are not part of this decision:

- `tools/check_single_engine.sh`: the same 9 FAIL lines as before;
- `imp-prices/tests/test_vendor_parity.py`: 2 FAIL (`causalbool.py` and
  `deconvolution.py`). These existed before adoption. The `deconvolution.py` drift now
  measures against the new canonical, and imp-prices was not touched;
- full CI and `make ci-local` were not run.
