# 02 — Historical plan: JIRA-style Tasks for the `doppel-Challenge` Implementation

> Historical planning document. Its version-1 complexity, detector, and
> acceptance wording is superseded by `00-protocol.md` version 2.0.0 and the
> executable interfaces/tests. It is retained for audit provenance only.

| Field | Value |
|---|---|
| Document | `02-plan.md` |
| Status | Implementation plan, version 1 |
| Parent | `doppel-Challenge/doc/00-protocol.md`, `01-record-schema.md` |
| Authors | A. Hernández-Espinosa (CausalBool group) |
| Date | 2026-09-09 |
| Scope | Task breakdown, acceptance criteria, veracity tests, dependencies, and post-conditions for every implementation unit required by the protocol. |

---

## 0. Purpose

This document is the JIRA-style implementation plan for the `doppel-Challenge` project. Every task is named, scoped, and accompanied by its dependencies, pre-conditions, post-conditions, acceptance criteria, and veracity tests. The plan is ordered so that a single engineer can execute it from top to bottom without re-deriving the structure. The plan is also structured so that each task's commit prefix `[AUDIT04-H/doppel-<task-id>]` carries the task identifier, satisfying the project governance.

The plan covers nine epics that mirror the protocol's stages, plus two cross-cutting epics (verification and write-up). Every task's acceptance criteria include both *technical correctness* (the unit test that the build must pass) and *veracity* (the property that the measurement is what the protocol claims). Veracity tests are the harder of the two: they exist because the protocol's contribution is the joint use of the CausalBool machinery, the divergence alarm, and the compression distance on a perturbation class, and a unit test that proves the code runs is not the same as a test that proves the measurement is the right one.

The plan is intentionally implementation-ready, not exploratory. It does not propose new theory; it specifies the work that has to be done to evaluate the protocol's theory and produce the write-up.

---

## 1. Conventions

### 1.1 Task Identifiers

Tasks are named `DOPPEL-<n>` for the implementation tasks and `DOPPEL-V-<n>` for the veracity tasks. Dependencies are stated explicitly; a task is `Ready` only when all dependencies are `Done`.

### 1.2 Status Vocabulary

| Status | Meaning |
|---|---|
| `Backlog` | Task is defined but not started. |
| `Ready` | All dependencies are `Done`; the task is unblocked. |
| `In Progress` | Active work; the assignee has begun. |
| `Review` | Work is complete; the author awaits peer review. |
| `Done` | Acceptance criteria, including all veracity tests, pass. |
| `Blocked` | Work cannot proceed without an external input. |

### 1.3 Commit Prefix

Every commit message starts with `[AUDIT04-H/doppel-<task-id>]`. The commit body names the deliverable and references the protocol section. The author is `Alberto <albertohernandezespinosa@gmail.com>`, with no AI co-authorship.

### 1.4 Test Convention

Unit tests live in `doppel-challenge/tests/`. Veracity tests live in `doppel-challenge/tests/veracity/`. The directory is mirror-imaged with the source tree under `doppel-challenge/src/`. The test runner is `pytest`. Coverage is reported by `pytest --cov=doppel_challenge` and is required to be at least 95% line coverage for `doppel-challenge/src/` at the end of every epic.

### 1.5 Path Convention

All paths are relative to the repository root. The implementation lives under `doppel-challenge/src/`, the tests under `doppel-challenge/tests/`, the artefacts under `doppel-challenge/configs/`, `doppel-challenge/catalogues/`, and `doppel-challenge/aggregated/`, and the figures under `doppel-challenge/figures/`. Existing CausalBool modules are imported and not modified.

---

## 2. Epic Map

| Epic | Tasks | Purpose |
|---|---|---|
| E1 — Configuration and record layer | DOPPEL-1 to DOPPEL-3 | Configuration record, JSONL writer, record validator. |
| E2 — Repertoire and attractor pipeline | DOPPEL-4 to DOPPEL-8 | Repertoire computation, attractor enumeration, probability distribution, and the existing-routine integration. |
| E3 — Compression layer | DOPPEL-9 to DOPPEL-12 | (decimals, summandos) compression, per-column schema length, and NCD computation. |
| E4 — Perturbation enumeration | DOPPEL-13 to DOPPEL-15 | Graph-distance ball enumeration, perturbation kinds, and the per-perturbation serial recomputation loop. |
| E5 — Statistics layer | DOPPEL-16 to DOPPEL-20 | KL divergence, Jaccard support distance, NCD, expected loss, and the catalogue-membership test. |
| E6 — Catalogue and configuration driver | DOPPEL-21 to DOPPEL-23 | The nine-stage driver that runs a single configuration end-to-end. |
| E7 — Sweep and aggregation | DOPPEL-24 to DOPPEL-26 | The sweep runner and the sweep aggregate. |
| E8 — Figures and write-up | DOPPEL-27 to DOPPEL-30 | The six canonical figures and the write-up draft. |
| E9 — Verification and reproducibility | DOPPEL-V-1 to DOPPEL-V-7 | Veracity tests, golden catalogues, and reproducibility harness. |

The ordering is also the dependency order: a task in E2 may depend on tasks in E1, but not on E3 or later.

---

## 3. Epic E1 — Configuration and Record Layer

### Task DOPPEL-1 — Configuration record writer

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | None |
| Pre-conditions | `01-record-schema.md` Section 2 is approved. |
| Post-conditions | A `configuration` record is written to `doppel-challenge/configs/<config_id>.json` for any valid input; the file is JSON, schema-valid, and `sha256` is correct. |

Description. Implement `doppel-challenge/src/records.py` with `write_configuration(N, k, library_id, library_gates, library_max_arity, graph_constraint, loss_id, loss_params, C_policy, sampling, budget) -> str` that returns the `config_id` (a ULID) and writes the record.

Acceptance criteria.

- **AC1.** `pytest tests/test_records.py::test_write_configuration_roundtrip` passes: write then read, fields equal.
- **AC2.** `pytest tests/test_records.py::test_configuration_sha256_is_stable` passes: the `sha256` field is reproducible across two invocations with the same input.
- **AC3.** The output is rejected by the validator if any required field is missing or out of range.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_records_vt1_schema_conformance.py` passes: the record conforms to the JSON schema under `doppel-challenge/schemas/configuration.schema.json`.

### Task DOPPEL-2 — JSONL writer

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-1 |
| Pre-conditions | `01-record-schema.md` Section 1.1 is approved. |
| Post-conditions | Any iterable of records can be appended to a `.jsonl` file, one record per line, with stable `sha256`. |

Description. Implement `doppel_challenge.io.write_jsonl(path, records)` and `doppel_challenge.io.read_jsonl(path)`.

Acceptance criteria.

- **AC1.** `pytest tests/test_io.py::test_write_read_jsonl_roundtrip` passes.
- **AC2.** Each line is a single valid JSON object terminated by `\n`; no empty lines; no multi-line records.
- **AC3.** The reader is strict: a line that does not parse is a hard error and the error names the line number and the failing record.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_io_vt1_path_conformance.py` passes: every record written to a path under `catalogues/` is readable back without change.

### Task DOPPEL-3 — Record validator

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-1, DOPPEL-2 |
| Pre-conditions | The JSON schemas under `doppel-challenge/schemas/` exist. |
| Post-conditions | Every record is validated on write and on read; mismatches raise `doppel_challenge.errors.RecordError` and the message names the failing `sha256`. |

Description. Implement `doppel_challenge.io.validate_record(record)` and the JSON schemas under `doppel-challenge/schemas/`.

Acceptance criteria.

- **AC1.** `pytest tests/test_io.py::test_validate_rejects_unknown_kind` passes: an unknown `record_kind` is rejected.
- **AC2.** `pytest tests/test_io.py::test_validate_rejects_bad_sha256` passes: a record with a wrong `sha256` is rejected.
- **AC3.** `pytest tests/test_io.py::test_validate_enforces_support_invariant` passes: a `support_row` whose `support_intersection` size does not equal the Jaccard invariant is rejected.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_validator_vt1_field_ranges.py` passes: every numerical field is in the declared range for a hand-checked catalogue.

---

## 4. Epic E2 — Repertoire and Attractor Pipeline

### Task DOPPEL-4 — Repertoire computation

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-3 |
| Pre-conditions | `index-deconvolution/src/causalbool.py::repertoire` is importable. |
| Post-conditions | Given $(A, \theta)$ with $N \le 20$, the function returns the exhaustive output repertoire as a `(counts, support, probs)` triple, identical to the matrix returned by `causalbool.repertoire(net)`. |

Description. Implement `doppel_challenge.repertoire.compute(A, theta, params) -> dict`. The function calls `causalbool.repertoire(Network(n=N, C=A, gates=theta, params=params))` and returns the result packaged into the `repertoire` block of the record schema.

Acceptance criteria.

- **AC1.** `pytest tests/test_repertoire.py::test_compute_repertoire_is_deterministic` passes: two calls on the same input return identical outputs.
- **AC2.** `pytest tests/test_repertoire.py::test_compute_repertoire_matches_causalbool` passes: the returned matrix is equal element-wise to `causalbool.repertoire` for $N \in \{4, 5, 6\}$.
- **AC3.** `pytest tests/test_repertoire.py::test_compute_repertoire_row_count_is_2_to_the_N` passes: `rows = 2**N`.
- **AC4.** `pytest tests/test_repertoire.py::test_compute_repertoire_probs_sum_to_one` passes: `sum(probs) == 1` within $10^{-12}$.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_repertoire_vt1_lsb_first.py` passes: the matrix is LSB-first, verified by a hand-checked $N=4$ case.
- **VT2.** `pytest tests/veracity/test_repertoire_vt2_attractor_inclusion.py` passes: every state in the support is reachable from some initial state under the network (the support is the union of all attractor states).

### Task DOPPEL-5 — Attractor enumeration

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-4 |
| Pre-conditions | `reprogramming.num_attractors` and `reprogramming.image_size` are importable. |
| Post-conditions | Given $(A, \theta)$, the function returns the number of attractors, the size of each attractor, and the set of states in the support. The implementation is exact and linear in $2^N$. |

Description. Implement `doppel_challenge.attractors.enumerate(A, theta, params) -> dict` with fields `n_attractors`, `attractor_sizes`, `support`.

Acceptance criteria.

- **AC1.** `pytest tests/test_attractors.py::test_attractor_count_matches_reprogramming` passes: `n_attractors` equals `reprogramming.num_attractors(net)` for $N \in \{4, 5, 6\}$.
- **AC2.** `pytest tests/test_attractors.py::test_attractor_sizes_partition_support` passes: the multiset union of attractor sizes equals the size of the support.
- **AC3.** `pytest tests/test_attractors.py::test_attractor_enumeration_is_exact` passes: for a fixed-point network, every state is its own attractor; the function returns $|\mathrm{supp}| = 2^N$.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_attractors_vt1_each_attractor_is_a_cycle.py` passes: every reported attractor is in fact a cycle of the next-state function; verified by recomputing the next-state map and confirming the cycle.
- **VT2.** `pytest tests/veracity/test_attractors_vt2_no_attractor_is_a_subset_of_another.py` passes: no reported attractor is a strict subset of another.

### Task DOPPEL-6 — Repertoire probability distribution

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-4 |
| Pre-conditions | The repertoire matrix is computed. |
| Post-conditions | The probability distribution is the empirical distribution over the support with mass proportional to the total number of visits across the $2^N$ initial states. The mass is well-defined and sums to 1. |

Description. The probability distribution is already part of `compute_repertoire`. This task packages the function and adds a `probs_from_counts(counts, support)` helper for clarity.

Acceptance criteria.

- **AC1.** `pytest tests/test_repertoire.py::test_probs_from_counts_is_uniform_on_unit_mass` passes.
- **AC2.** `pytest tests/test_repertoire.py::test_probs_from_counts_sums_to_one` passes.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_repertoire_vt3_visits_equal_repertoire.py` passes: the per-support visit counts in `compute_repertoire` are equal to the column-wise visit counts of the next-state function applied to all $2^N$ initial states.

### Task DOPPEL-7 — Repertoire veracity unit test

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-4, DOPPEL-5, DOPPEL-6 |
| Pre-conditions | All E2 tasks are done. |
| Post-conditions | A single hand-checked golden catalogue at $N=4$ exercises the entire E2 pipeline and is committed to `doppel-challenge/tests/golden/E2_N4/`. |

Description. Build the golden catalogue: a hand-checked base network at $N=4$, its repertoire, its attractors, and the corresponding counts and probabilities. Commit the file. The test loads the file and compares.

Acceptance criteria.

- **AC1.** `pytest tests/veracity/test_golden_E2_N4.py::test_full_pipeline_matches_golden` passes.

Veracity tests.

- **VT1.** The golden file is generated once by hand and frozen; the test is the canonical proof that the pipeline reproduces a hand-checked result byte-for-byte.

### Task DOPPEL-8 — `pytest.ini` and coverage configuration

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | None |
| Pre-conditions | `pytest` and `pytest-cov` are installed. |
| Post-conditions | `pytest` runs the test suite under `doppel-challenge/tests/`; coverage is reported; tests in `doppel-challenge/tests/veracity/` are tagged and run by default. |

Description. Configure `doppel-challenge/pytest.ini` and `doppel-challenge/.coveragerc` to enforce the conventions of Section 1.4 and 1.5.

Acceptance criteria.

- **AC1.** `pytest doppel-challenge/tests/ --co` lists every test under `doppel-challenge/tests/`.
- **AC2.** `pytest doppel-challenge/tests/ --cov=doppel_challenge --cov-report=term-missing` reports coverage for `doppel-challenge/src/`.

Veracity tests.

- **VT1.** A new test file dropped under `doppel-challenge/tests/veracity/` is picked up automatically by the next `pytest` run.

---

## 5. Epic E3 — Compression Layer

### Task DOPPEL-9 — Per-column schema length

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-4 |
| Pre-conditions | `description_lengths.schema_normal_form_length` is importable. |
| Post-conditions | Given a column of the repertoire, the function returns the bit length of the per-node `(decimals, summandos)` compression. |

Description. Implement `doppel_challenge.compression.column_bits(column, n) -> int` that wraps `description_lengths.schema_normal_form_length`.

Acceptance criteria.

- **AC1.** `pytest tests/test_compression.py::test_column_bits_is_nonnegative` passes: returns a non-negative integer.
- **AC2.** `pytest tests/test_compression.py::test_column_bits_matches_schema_length` passes: for $N=4$, the value matches the Wolfram `AlphaSchemaBits` reference.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_compression_vt1_round_trip.py` passes: the schema normal form decodes back to the column exactly, for $N \le 6$ and all gate families.

### Task DOPPEL-10 — Repertoire compression

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-9 |
| Pre-conditions | The repertoire matrix is computed. |
| Post-conditions | The function returns the `(decimal_bits, summandos_bits, L_CB_bits)` triple for the repertoire, summing `column_bits` over columns. |

Description. Implement `doppel_challenge.compression.repertoire_bits(repertoire_dict) -> dict`.

Acceptance criteria.

- **AC1.** `pytest tests/test_compression.py::test_repertoire_bits_sums_columns` passes.
- **AC2.** `pytest tests/test_compression.py::test_repertoire_bits_is_reproducible` passes.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_compression_vt2_satisfies_ait_bound.py` passes: $L_{\mathrm{CB}}(\mu) \ge K(\mu) - c$ for the canonical CausalBool constant $c$, verified on a small set of reference repertoires.

### Task DOPPEL-11 — NCD computation

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-10 |
| Pre-conditions | The compressor is deterministic. |
| Post-conditions | The function returns the normalised compression distance between two repertoires. The output is in $[0, 1+\epsilon]$ and is symmetric. |

Description. Implement `doppel_challenge.compression.ncd(rep_a, rep_b) -> float`.

Acceptance criteria.

- **AC1.** `pytest tests/test_compression.py::test_ncd_is_zero_for_identical` passes.
- **AC2.** `pytest tests/test_compression.py::test_ncd_is_symmetric` passes within $10^{-9}$.
- **AC3.** `pytest tests/test_compression.py::test_ncd_is_bounded_by_one_plus_epsilon` passes.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_compression_vt3_ncd_universality.py` passes: for two repertoires whose compression lengths are equal and concatenation length is the maximum, NCD returns 0.

### Task DOPPEL-12 — Compression veracity unit test

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-9, DOPPEL-10, DOPPEL-11 |
| Pre-conditions | E3 tasks done. |
| Post-conditions | A hand-checked golden compression catalogue at $N=4$ is committed. |

Acceptance criteria.

- **AC1.** `pytest tests/veracity/test_golden_E3_N4.py::test_compression_matches_golden` passes.

Veracity tests.

- **VT1.** The golden file is generated by hand and frozen.

---

## 6. Epic E4 — Perturbation Enumeration

### Task DOPPEL-13 — Graph-distance ball enumeration

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-3 |
| Pre-conditions | The configuration declares the perturbation kind and the distance budget $k$. |
| Post-conditions | The function returns the list of perturbed adjacency matrices in $\mathcal{P}_k(A_0)$ as a deterministic, indexable sequence. |

Description. Implement `doppel_challenge.perturbations.ball(A0, k, kind) -> list` with `kind in {"EDGE_FLIP", "EDGE_ADD", "EDGE_REMOVE"}`.

Acceptance criteria.

- **AC1.** `pytest tests/test_perturbations.py::test_ball_includes_A0_when_k_is_zero` passes.
- **AC2.** `pytest tests/test_perturbations.py::test_ball_size_matches_combinatorial_bound` passes: $|\mathcal{P}_k| \le \binom{N^2}{k}$ for `EDGE_FLIP`.
- **AC3.** `pytest tests/test_perturbations.py::test_ball_is_deterministic_under_seed` passes.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_perturbations_vt1_no_duplicates.py` passes: no matrix appears twice in the ball.
- **VT2.** `pytest tests/veracity/test_perturbations_vt2_minimum_distance_is_one.py` passes: every non-identity element of $\mathcal{P}_1$ differs from $A_0$ in exactly one entry.

### Task DOPPEL-14 — Perturbation index

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-13 |
| Pre-conditions | The enumeration is indexable. |
| Post-conditions | Every perturbation has a unique `perturbation_index` in $[0, |\mathcal{P}_k|)$. The index is reproducible. |

Description. Implement `doppel_challenge.perturbations.index(A0, A, kind) -> int`.

Acceptance criteria.

- **AC1.** `pytest tests/test_perturbations.py::test_index_is_unique` passes.
- **AC2.** `pytest tests/test_perturbations.py::test_index_roundtrip` passes: `ball(A0, k)[index(A0, A, kind)] == A` for $A$ in the ball.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_perturbations_vt3_index_stable_across_runs.py` passes.

### Task DOPPEL-15 — Serial recomputation loop

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-13, DOPPEL-14, DOPPEL-4, DOPPEL-5, DOPPEL-6 |
| Pre-conditions | All E2 tasks are done. |
| Post-conditions | Given $(A_0, \theta_0)$ and $k$, the loop iterates $\mathcal{P}_k(A_0)$ in index order, computes the repertoire and the attractor summary for each $A$, and writes the `catalogue_row` records. The runtime is linear in the number of perturbations and in $N$. |

Description. Implement `doppel_challenge.perturbations.serial_sweep(A0, theta0, params, k, kind, config_id, output_path) -> None`.

Acceptance criteria.

- **AC1.** `pytest tests/test_perturbations.py::test_serial_sweep_writes_records` passes: the output file exists and is a valid JSONL.
- **AC2.** `pytest tests/test_perturbations.py::test_serial_sweep_is_deterministic` passes.
- **AC3.** `pytest tests/test_perturbations.py::test_serial_sweep_runtime_is_linear_in_N` passes: doubling $N$ at fixed $k$ approximately quadruples the runtime, within a constant.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_perturbations_vt4_sweep_matches_known_catalogue.py` passes: the sweep at $N=4$, $k=1$ matches the golden catalogue.

---

## 7. Epic E5 — Statistics Layer

### Task DOPPEL-16 — KL divergence

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-4 |
| Pre-conditions | Two repertoire dictionaries are available. |
| Post-conditions | The function returns the Kullback–Leibler divergence $D_{\mathrm{KL}}(\mu_A \| \mu_0)$ in nats, or `None` when the supports are disjoint. |

Description. Implement `doppel_challenge.stats.kl(p_dict, q_dict) -> float | None`.

Acceptance criteria.

- **AC1.** `pytest tests/test_stats.py::test_kl_is_zero_for_identical` passes.
- **AC2.** `pytest tests/test_stats.py::test_kl_is_nonnegative` passes.
- **AC3.** `pytest tests/test_stats.py::test_kl_returns_none_for_disjoint_support` passes.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_stats_vt1_kl_matches_scipy.py` passes: the value matches `scipy.special.rel_entr(p, q).sum()` for a hand-checked pair.

### Task DOPPEL-17 — Jaccard support distance

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-4 |
| Pre-conditions | Two repertoire dictionaries are available. |
| Post-conditions | The function returns the Jaccard distance in $[0, 1]$. |

Description. Implement `doppel_challenge.stats.jaccard(p_dict, q_dict) -> float`.

Acceptance criteria.

- **AC1.** `pytest tests/test_stats.py::test_jaccard_is_zero_for_identical_support` passes.
- **AC2.** `pytest tests/test_stats.py::test_jaccard_is_one_for_disjoint_support` passes.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_stats_vt2_jaccard_matches_manual.py` passes: for two hand-checked supports, the function returns the Jaccard distance computed by hand.

### Task DOPPEL-18 — NCD statistic

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-11, DOPPEL-4 |
| Pre-conditions | The compressor is implemented. |
| Post-conditions | The function returns the NCD between two repertoires. |

Description. The function is a thin wrapper around `doppel_challenge.compression.ncd`. This task adds the loss-row / NCD-row writer that records the per-perturbation NCD.

Acceptance criteria.

- **AC1.** `pytest tests/test_stats.py::test_ncd_writer_writes_records` passes.
- **AC2.** `pytest tests/test_stats.py::test_ncd_writer_is_deterministic` passes.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_stats_vt3_ncd_writer_matches_golden.py` passes.

### Task DOPPEL-19 — Expected loss

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-4 |
| Pre-conditions | The configuration declares the loss function. |
| Post-conditions | The function returns $\ell(A) = \sum_x \mu_A(x) s(x)$ for the chosen loss. |

Description. Implement `doppel_challenge.stats.expected_loss(p_dict, loss_id, loss_params) -> float`.

Acceptance criteria.

- **AC1.** `pytest tests/test_stats.py::test_loss_indicator_is_at_most_one` passes.
- **AC2.** `pytest tests/test_stats.py::test_loss_linear_matches_definition` passes.
- **AC3.** `pytest tests/test_stats.py::test_loss_entropy_matches_definition` passes: $s(x) = -\log p_0(x)$ and $\ell = -\sum_{x \in \mathrm{supp}(\mu_A)} \mu_A(x) \log p_0(x)$.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_stats_vt4_loss_matches_manual.py` passes.

### Task DOPPEL-20 — Catalogue-membership test

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-4, DOPPEL-5 |
| Pre-conditions | A catalogue and a query repertoire are available. |
| Post-conditions | The function returns `True` iff the query repertoire is in the catalogue up to the declared tolerance. The tolerance is the Jaccard distance. |

Description. Implement `doppel_challenge.stats.in_catalogue(query, catalogue, tol) -> bool`.

Acceptance criteria.

- **AC1.** `pytest tests/test_stats.py::test_in_catalogue_returns_true_for_exact_match` passes.
- **AC2.** `pytest tests/test_stats.py::test_in_catalogue_returns_false_for_disjoint` passes.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_stats_vt5_in_catalogue_matches_golden.py` passes.

---

## 8. Epic E6 — Catalogue and Configuration Driver

### Task DOPPEL-21 — Stage 1 and 2 driver

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-1, DOPPEL-4, DOPPEL-5, DOPPEL-6 |
| Pre-conditions | The configuration and the base network are produced. |
| Post-conditions | `doppel_challenge.driver.run_stage_1_and_2(config) -> (config_id, base_record)` writes the configuration and the base network records. |

Acceptance criteria.

- **AC1.** `pytest tests/test_driver.py::test_stage_1_2_writes_records` passes.
- **AC2.** `pytest tests/test_driver.py::test_stage_1_2_is_deterministic_under_seed` passes.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_driver_vt1_golden_base.py` passes.

### Task DOPPEL-22 — Stage 3 to 8 driver

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-21, all of E4 and E5 |
| Pre-conditions | The base network exists. |
| Post-conditions | `doppel_challenge.driver.run_stage_3_to_8(config, base) -> None` produces the per-stage JSONL files, the joint record file, and the runtime trace. |

Acceptance criteria.

- **AC1.** `pytest tests/test_driver.py::test_stage_3_8_writes_all_files` passes.
- **AC2.** `pytest tests/test_driver.py::test_stage_3_8_inner_join_is_consistent` passes: every joint row has matching fields across the per-stage rows.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_driver_vt2_golden_full_pipeline.py` passes: the full pipeline at $N=4$, $k=1$ matches the golden file.

### Task DOPPEL-23 — Stage 9 driver

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-22 |
| Pre-conditions | The joint file is written. |
| Post-conditions | `doppel_challenge.driver.run_stage_9(config, joint_path) -> None` writes the sweep aggregate record. |

Acceptance criteria.

- **AC1.** `pytest tests/test_driver.py::test_stage_9_writes_sweep_aggregate` passes.
- **AC2.** `pytest tests/test_driver.py::test_stage_9_optimal_attacker_is_in_catalogue` passes.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_driver_vt3_optimal_attacker_matches_golden.py` passes.

---

## 9. Epic E7 — Sweep and Aggregation

### Task DOPPEL-24 — Configuration sweep

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-23 |
| Pre-conditions | A sweep definition is provided. |
| Post-conditions | `doppel_challenge.sweep.run(sweep_def) -> sweep_id` runs every configuration in the sweep, writes every artefact, and returns the sweep identifier. |

Acceptance criteria.

- **AC1.** `pytest tests/test_sweep.py::test_sweep_runs_all_configurations` passes.
- **AC2.** `pytest tests/test_sweep.py::test_sweep_is_resumable` passes: a partial run is resumed and completed.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_sweep_vt1_golden_sweep.py` passes: a $3 \times 2$ sweep at small $N$ matches the golden sweep output.

### Task DOPPEL-25 — Sweep aggregate

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-24 |
| Pre-conditions | All configurations in the sweep are run. |
| Post-conditions | The aggregate JSONL file is written; one record per configuration; all fields per the schema. |

Acceptance criteria.

- **AC1.** `pytest tests/test_sweep.py::test_sweep_aggregate_writes_records` passes.
- **AC2.** `pytest tests/test_sweep.py::test_sweep_aggregate_summary_stats_match_definition` passes: the min, max, mean, and std are computed over the catalogue of each configuration.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_sweep_vt2_aggregate_matches_golden.py` passes.

### Task DOPPEL-26 — Sweep reproducer

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-25 |
| Pre-conditions | The aggregate exists. |
| Post-conditions | Given a sweep identifier, the reproducer runs the same sweep on the same hardware and produces byte-identical records (modulo timestamps). |

Acceptance criteria.

- **AC1.** `pytest tests/test_sweep.py::test_sweep_reproducer_runs_again` passes.
- **AC2.** `pytest tests/test_sweep.py::test_sweep_reproducer_records_have_stable_sha256` passes: the `sha256` of every record is identical across two runs (timestamps normalised).

Veracity tests.

- **VT1.** `pytest tests/veracity/test_sweep_vt3_reproducibility.py` passes: a two-run sweep produces identical `sha256` digests for every record, and the implementation explicitly tests this.

---

## 10. Epic E8 — Figures and Write-up

### Task DOPPEL-27 — Loss vs KL scatter

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-25 |
| Pre-conditions | The sweep aggregate is written. |
| Post-conditions | `doppel-challenge/figures/<sweep_id>/loss_vs_kl.png` is a 300 DPI scatter plot of $\ell$ vs $D_{\mathrm{KL}}$ for every catalogue, with the constraint $D_{\mathrm{KL}} \le C$ overlaid. |

Acceptance criteria.

- **AC1.** `pytest tests/test_figures.py::test_loss_vs_kl_is_generated` passes.
- **AC2.** The figure has a CSV sibling at the same path with the underlying data.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_figures_vt1_data_matches_csv.py` passes: the figure's underlying data is exactly the CSV.

### Task DOPPEL-28 — Lipschitz profile

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-25 |
| Pre-conditions | The sweep aggregate is written. |
| Post-conditions | `lipschitz_profile.png` is a scatter of $D_{\mathrm{KL}}$ vs graph distance, with the empirical envelope. |

Acceptance criteria.

- **AC1.** `pytest tests/test_figures.py::test_lipschitz_profile_is_generated` passes.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_figures_vt2_envelope_is_monotone.py` passes: the empirical envelope is non-decreasing in the graph distance, up to sampling noise.

### Task DOPPEL-29 — Support mismatch, NCD vs KL, defender advantage, complexity distribution

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-25 |
| Pre-conditions | The sweep aggregate is written. |
| Post-conditions | The four remaining figures are generated. Each has a CSV sibling. |

Acceptance criteria.

- **AC1.** `pytest tests/test_figures.py::test_all_canonical_figures_generated` passes.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_figures_vt3_defender_advantage_monotone_in_C.py` passes: detection probability is non-increasing in $C$ for both detectors.

### Task DOPPEL-30 — Write-up draft

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-27, DOPPEL-28, DOPPEL-29 |
| Pre-conditions | The figures and the aggregates exist. |
| Post-conditions | A draft of the write-up in `doppel-challenge/writeup/main.tex` is committed. The draft follows the master project's paper template: abstract, introduction, methods, results, discussion, references. |

Acceptance criteria.

- **AC1.** The draft compiles under the master project's `pdflatex` chain.
- **AC2.** Every figure is referenced by the draft and is generated from the committed data.
- **AC3.** The draft is committed as a single commit with the prefix `[AUDIT04-H/doppel-writeup-v1]`.

Veracity tests.

- **VT1.** `pytest tests/veracity/test_writeup_vt1_figures_referenced.py` passes: every figure file in `figures/` is referenced in the draft.

---

## 11. Epic E9 — Verification and Reproducibility

### Task DOPPEL-V-1 — Forward/reverse identity

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-7 |
| Pre-conditions | A golden base network at $N=4$ exists. |
| Post-conditions | The forward CausalBool transform applied to the recovered network reproduces the original repertoire exactly. This is the deconvolution's provably non-circular test. |

Acceptance criteria.

- **AC1.** `pytest tests/veracity/test_veracity_V1_forward_reverse.py::test_recovered_network_reproduces_repertoire` passes.

### Task DOPPEL-V-2 — Perturbation cataloguing

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-13, DOPPEL-15 |
| Pre-conditions | The catalogue is enumerated. |
| Post-conditions | The catalogue at $N=4$, $k=1$ contains every perturbed repertoire in the hand-checked golden catalogue. |

Acceptance criteria.

- **AC1.** `pytest tests/veracity/test_veracity_V2_catalogue_completeness.py::test_catalogue_matches_golden` passes.

### Task DOPPEL-V-3 — Compression AIT bound

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-10 |
| Pre-conditions | The compressor is implemented. |
| Post-conditions | For every repertoire in the golden catalogue, $L_{\mathrm{CB}}(\mu) \ge K(\mu) - c$ for the canonical CausalBool constant $c$. The constant is reported by the test. |

Acceptance criteria.

- **AC1.** `pytest tests/veracity/test_veracity_V3_ait_bound.py::test_bound_holds` passes.

### Task DOPPEL-V-4 — Catalogue-membership test calibration

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-20 |
| Pre-conditions | The catalogue-membership test is implemented. |
| Post-conditions | The test's detection probability on a held-out perturbation set is at least 0.95 at the chosen $C$. |

Acceptance criteria.

- **AC1.** `pytest tests/veracity/test_veracity_V4_catalogue_calibration.py::test_detection_probability` passes.

### Task DOPPEL-V-5 — Lipschitz profile sanity

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-25 |
| Pre-conditions | The sweep aggregate is written. |
| Post-conditions | The empirical envelope of $D_{\mathrm{KL}}$ vs graph distance is non-decreasing in the graph distance, up to sampling noise. |

Acceptance criteria.

- **AC1.** `pytest tests/veracity/test_veracity_V5_lipschitz_envelope.py` passes.

### Task DOPPEL-V-6 — Optimal-attacker consistency

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | DOPPEL-23 |
| Pre-conditions | The sweep aggregate is written. |
| Post-conditions | The reported optimal attacker is in the catalogue and has the highest $\ell$ under the constraint. |

Acceptance criteria.

- **AC1.** `pytest tests/veracity/test_veracity_V6_optimal_attacker_consistency.py` passes.

### Task DOPPEL-V-7 — End-to-end reproducibility

| Field | Value |
|---|---|
| Status | Ready |
| Owner | TBD |
| Dependencies | All of E1 through E7. |
| Pre-conditions | The full pipeline runs. |
| Post-conditions | A two-run reproducibility test produces byte-identical records (modulo timestamps and the reproducer's normalization). |

Acceptance criteria.

- **AC1.** `pytest tests/veracity/test_veracity_V7_reproducibility.py` passes.

---

## 12. Dependency Graph

The following edges are the strict dependencies. They are the only constraints on execution order beyond the epic ordering.

| Task | Depends on |
|---|---|
| DOPPEL-1 | — |
| DOPPEL-2 | DOPPEL-1 |
| DOPPEL-3 | DOPPEL-1, DOPPEL-2 |
| DOPPEL-4 | DOPPEL-3 |
| DOPPEL-5 | DOPPEL-4 |
| DOPPEL-6 | DOPPEL-4 |
| DOPPEL-7 | DOPPEL-4, DOPPEL-5, DOPPEL-6 |
| DOPPEL-8 | — |
| DOPPEL-9 | DOPPEL-4 |
| DOPPEL-10 | DOPPEL-9 |
| DOPPEL-11 | DOPPEL-10 |
| DOPPEL-12 | DOPPEL-9, DOPPEL-10, DOPPEL-11 |
| DOPPEL-13 | DOPPEL-3 |
| DOPPEL-14 | DOPPEL-13 |
| DOPPEL-15 | DOPPEL-13, DOPPEL-14, DOPPEL-4, DOPPEL-5, DOPPEL-6 |
| DOPPEL-16 | DOPPEL-4 |
| DOPPEL-17 | DOPPEL-4 |
| DOPPEL-18 | DOPPEL-11, DOPPEL-4 |
| DOPPEL-19 | DOPPEL-4 |
| DOPPEL-20 | DOPPEL-4, DOPPEL-5 |
| DOPPEL-21 | DOPPEL-1, DOPPEL-4, DOPPEL-5, DOPPEL-6 |
| DOPPEL-22 | DOPPEL-21, E4, E5 |
| DOPPEL-23 | DOPPEL-22 |
| DOPPEL-24 | DOPPEL-23 |
| DOPPEL-25 | DOPPEL-24 |
| DOPPEL-26 | DOPPEL-25 |
| DOPPEL-27 | DOPPEL-25 |
| DOPPEL-28 | DOPPEL-25 |
| DOPPEL-29 | DOPPEL-25 |
| DOPPEL-30 | DOPPEL-27, DOPPEL-28, DOPPEL-29 |
| DOPPEL-V-1 | DOPPEL-7 |
| DOPPEL-V-2 | DOPPEL-13, DOPPEL-15 |
| DOPPEL-V-3 | DOPPEL-10 |
| DOPPEL-V-4 | DOPPEL-20 |
| DOPPEL-V-5 | DOPPEL-25 |
| DOPPEL-V-6 | DOPPEL-23 |
| DOPPEL-V-7 | E1 through E7 |

Within an epic, the order is the listing order. Across epics, the order is E1 → E2 → E3 → E4 → E5 → E6 → E7 → E8 → E9.

---

## 13. Write-up Mapping

The write-up draft under E8 follows the master project's paper template. The mapping from sections to data sources is:

| Section | Data source | Tasks |
|---|---|---|
| Abstract | `sweep_aggregate` records | DOPPEL-25 |
| 1. Introduction | Protocol | `00-protocol.md` Section 1, 2 |
| 2. Methods | Protocol, schema | `00-protocol.md` Section 3, 4, 8; `01-record-schema.md` Section 5 |
| 3. Results | Figures, aggregates | DOPPEL-27 to DOPPEL-29, DOPPEL-25 |
| 4. Discussion | Theoretical framework | `00-protocol.md` Section 9 |
| 5. Conclusion | Veracity tests | DOPPEL-V-1 to DOPPEL-V-7 |
| References | Protocol | `00-protocol.md` Section 17 |

The write-up is not a restatement of the protocol; it cites the protocol and the record schema, and references the data files by `sha256`.

---

## 14. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| The CausalBool compressor is slower than the protocol assumes for $N > 12$. | The E3 tasks include a runtime regression test (DOPPEL-15 AC3). If the runtime is non-linear, the sweep is restricted to $N \le 12$ and a separate write-up section reports the scaling. |
| The catalogue-membership test has a high false-positive rate at the chosen $C$. | DOPPEL-V-4 calibrates the test on a held-out set. If the test does not reach 0.95, the write-up reports the actual rate and proposes a different $C$ policy. |
| The optimal-attacker search is dominated by a single configuration. | DOPPEL-15 records the full distribution; the write-up includes the entropy of $\ell$ over the catalogue as a robustness diagnostic. |
| The NCD is dominated by the natural repertoire, masking perturbations. | DOPPEL-V-3 and the figures in E8 surface the failure mode; the write-up's discussion section addresses it. |
| A unit test passes but a veracity test fails. | The acceptance criteria require both. The veracity tests run by default; the build is red if any fails. |

---

## 15. Acceptance Criteria Summary

A task is `Done` when:

1. The technical acceptance criteria (AC) pass under `pytest`.
2. The veracity tests (VT) pass under `pytest`.
3. The code is committed with the prefix `[AUDIT04-H/doppel-<task-id>]` and the author is `Alberto <albertohernandezespinosa@gmail.com>`.
4. The record artefacts have valid `sha256` digests.
5. The implementation does not modify any file outside `doppel-challenge/`.

The plan is `Done` when every task in E1 through E9 is `Done`, the sweep at the default configuration produces every canonical figure, the write-up draft compiles, and the veracity tests pass.

---

## 16. Amendment Log

| Date | Author | Amendment |
|---|---|---|
| 2026-09-09 | A. Hernández-Espinosa | Initial version. |
