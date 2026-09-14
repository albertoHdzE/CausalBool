# Record schema — version 2.0.0

The additive record kind `shared_program_benchmark` stores the exact shared
program payload, its conditional binary length, original-output BDM, independent
reference checks, and per-case validation/materialization scope. Its normative
contract and failure taxonomy are in [06-shared-program.md](06-shared-program.md).
Program identity uses `canonical_program_sha256`; the envelope digest also
includes experimental provenance. Runtime measurements are excluded from its
scientific digest, while the complete record remains SHA-256 sealed.

| Field | Value |
|---|---|
| Status | Authoritative schema documentation |
| Parent | `doc/00-protocol.md` |
| Version | `2.0.0` |
| Date | 2026-09-10 |

This document describes the records emitted by the implementation. Historical
version-1 files remain readable as audit inputs where their legacy digest is
known, but they are not regenerated or included in exact-study denominators.
New records are strict JSON and carry a complete SHA-256 seal.

## 1. Common envelope

Every new record has these fields:

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | Always `"2.0.0"` |
| `record_kind` | enum | One of the kinds listed below |
| `config_id` | string | Stable configuration identifier |
| `sweep_id` | string or null | Optional sweep identifier |
| `observable` | string or null | Scientific observable; exact rows use `basin_weighted_attractor_repertoire` |
| `approximation` | string or null | `none_exact_full_state_space`, `none_exact_compressed_owner`, or an explicit approximate method |
| `estimator_parameters` | object | Parameters needed to reproduce the estimator |
| `uncertainty` | object or null | Exactness or uncertainty method |
| `process_status` | string | Execution status, including `normal_exit`, `timeout`, or `crash` |
| `accepted_validation` | boolean | Relevant exactness and process gates passed; not a quality score |
| `provenance` | object or null | Source, environment, and configuration provenance |
| `scientific_digest` | string | Digest after removing only volatile execution metadata |
| `sha256` | string | Digest of the complete record with `sha256` blanked |
| `created_at` | ISO-8601 string | Volatile record creation time |

Records are canonicalised as sorted-key JSON without whitespace and with
`sha256` set to `""` before computing `sha256`. Non-finite numeric values are
never written to JSON. Infinite KL is represented by a null numeric value plus
explicit status fields.

## 2. Record kinds and locations

The implementation currently emits:

`configuration`, `base_network`, `catalogue_row`, `diagnostic`,
`catalogue_manifest`, `approximate_repertoire`, `scaling_benchmark`,
`full_behaviour_scaling_benchmark`, `whole_repertoire_scaling_benchmark`,
`scale_pilot`, and `scale_pilot_case`. The parent package also reserves
`loss_row`, `kl_row`, `support_row`, `ncd_row`, `joint_row`, `sweep_aggregate`,
`figure_manifest`, `runtime_trace`, and `exclusion` for additive workflows.

An exact run directory contains:

```text
config.json       configuration record
base.json         base_network record
catalogue.jsonl   append-only catalogue_row/diagnostic attempt history
checkpoints/      one atomically written record per perturbation id
manifest.json     catalogue_manifest record
summary.json      human-readable run summary
progress.json     execution progress
```

The exact and approximate namespaces are separate. Approximate records may
never use `none_exact_full_state_space`, and their `accepted_validation` flag
is false until a separately declared validation gate says otherwise.

## 3. Exact repertoire block

`base_network.repertoire` and `catalogue_row.repertoire` contain:

| Field | Meaning |
|---|---|
| `rows` | `2**N` initial states |
| `cols` | `N` nodes |
| `matrix_lsb_first` | Always true for this adapter |
| `transition_map` | Exact integer successor for every state |
| `one_step_output_distribution` | Separate uniform-input one-step histogram |
| `attractor_cycles` | Canonically sorted exact cycles |
| `basin_sizes` | Number of initial states reaching each cycle |
| `phase_weights` | Exact `{numerator, denominator}` weight per cycle (the same weight applies to every state in that cycle) |
| `support` | Sorted union of all attractor states |
| `counts` | Positive numerators on a common exact denominator |
| `probability_denominator` | Sum of `counts` |
| `probability_fractions` | Reduced exact fraction per support state |
| `probs` | Floating-point display values derived from exact fractions |
| `observable` | `basin_weighted_attractor_repertoire` |

The exact probability is the basin weight multiplied by the uniform phase
weight of the eventual cycle. `counts` are not raw trajectory visit counts;
they are a common-denominator representation of those phase-averaged
probabilities.

## 4. Catalogue rows

An exact `catalogue_row` additionally contains:

```text
A, gates, params, N
perturbation_kind, perturbation_id, is_identity, changed_edges, graph_distance
indegrees
loss_id, loss_params, ell
D_KL_nats, infinite_kl, divergence_status
p_mass_outside_q_support, conditional_D_KL_nats
support, total_variation, jensen_shannon
compression, native_mechanism, validation
```

`changed_edges` records `target`, `source`, and `operation`. `support` is the
Jaccard support-distance block. `compression` records the custom distribution
codec and NCD; `native_mechanism` is a distinct mechanism payload. An accepted
exact row has normal process status and a successful independent-owner,
codec, and metric validation. A row with infinite forward KL has
`D_KL_nats: null`, never a silently substituted finite value.

`diagnostic` records preserve failures and include the stable perturbation ID,
process status, failure class, message, provenance, and the same exact/approx-
imate namespace markers needed to keep them out of accepted denominators.

## 5. Manifest

`catalogue_manifest` records:

```text
manifest_kind, catalogue_path, checkpoint_path
expected_perturbation_ids, latest_perturbation_ids
n_attempt_records, n_latest_records, n_accepted, n_failures
scientific_digest, provenance
```

The release validator checks that expected and latest IDs match the latest
record for every perturbation, IDs are unique, counts agree, all rows belong
to the exact namespace, and the manifest itself is sealed.

## 6. Approximate records

`approximate_repertoire` and scaling records expose `observable`,
`approximation`, `estimator_parameters`, `uncertainty`, `convergence`,
`process_status`, `accepted_validation`, provenance, and resource metadata.
Approximate convergence is an explicit status, not implied by normal process
exit. A finite-horizon tail fallback is recorded as incomplete and cannot be
used to claim an exact long-run result.

## 7. Scientific digest exclusions

The scientific digest excludes only volatile execution metadata: creation and
run IDs, elapsed/runtime measurements, memory measurements, kernel log
prefixes, and remaining-time estimates. It retains the scientific payload,
configuration, source/environment provenance, estimator parameters, and
failure status. This makes repeated runs comparable without erasing the
conditions under which they were produced.

## 8. Validation entry points

- `validate_record(record)` validates schema version, digest, finite JSON,
  exact/approximate namespace, and KL status invariants.
- `validate_repertoire(net, rep)` compares the production owner with the
  independent trajectory oracle and checks transition maps, cycles, basin
  sizes, phase weights, support, and exact rational probabilities.
- `validate_catalogue_manifest(manifest, rows)` checks manifest coverage.
- `run_release_gate(study_dir)` audits every exact run and reports missing
  optional dependencies without converting them into scientific results.

`accepted_validation` is therefore a gate result for the declared record, not
a general-purpose confidence score.
