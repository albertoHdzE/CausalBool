# audit_r3 field inventory

The inventory was fixed in `src/audit_r3.py` (and the cases in `src/probe_matrix_r3.py`)
before the matrix first ran; this document was written afterwards and describes that code.

The audit uses the following conventions throughout:

- **int** means a built-in `int`, with `bool` excluded.
- **exact** means a recursive, type-exact comparison with the value recomputed
  independently by `src/expected_r3.py` from the frozen audit's primitives. Under it, `1`,
  `1.0` and `true` are three different values, and an absent key differs from `null`.
- **INVALID** issues carry `where`, `field` (the path) and `check`.

## Evidence semantics

| situation | label |
|---|---|
| file absent (cell artifact, JSONL, table, alphas, summary, seal entry, frozen identity) | missing evidence, INCOMPLETE |
| declared record absent from a present JSONL | missing (counted in `candidates`) |
| present file or record that is malformed, lacks a **required field**, carries an **undeclared field**, or has a wrong type, shape, range or value | INVALID, with the field path |
| both at once | INVALID; both lists are kept and independent checks continue |

No required scientific field is defaulted. `art.get("K", K)` in the frozen certificate is
reachable only after the inventory check: the cell inventory forbids `K`, and the FX1
inventory requires it and checks it exactly.

## Inventory by object

| object | declared keys (exact set unless stated) | checks |
|---|---|---|
| `cases.json` | consumed: `cells`, `expected_counts`, `mode` (key set not enforced; the prose keys `candidate_record_id`, `domain`, `run_id` and `tasks` are ignored) | r2 typed schema; `cells` and `expected_counts` exact against `protocol/CASES.json`; `mode` must equal `"production"`; consistent n/N/tau per model |
| `tables/<M>.json` | `model n N tau auto_action_ids actions tables` | `model`, `n`, `N` and `tau` exact against the declaration; `auto_action_ids` exact `[0]`; each action has exactly `action_id op j c name`, compared exactly with `{q, study.track_d_q(n)[q], study.q_name}`; the frozen range and owner-equality checks follow |
| `candidate_alphas/<M>.json` | `model candidates`; entry `id candidate alpha` | `model` exact; length = declared; `id` and the `candidate` descriptor exact against `study.candidates(n)`; `alpha` exact against the recomputed first-appearance vector |
| `cells/cell_XX.json` | exactly `freeze.json schema.cell_fields` (17 keys) | r2 structural schema; `cell_id model task regime n N` exact against the declared cell; `action_ids` exact `range(n_actions)`; `outputs` exact against the declared task; `coarsening` and `witnesses` non-null; frozen certificate and witness replay; `summary` exact against the independent summary |
| witness | `round from_stage to_stage first_separation_stage x y word word_names path_x path_y outputs_x outputs_y` | the frozen replay checks pair, word, paths and outputs; r3 adds `from_stage = round`, `to_stage = round+1`, `first_separation_stage = len(word)` and `word_names` = `study.q_name` of each letter, all exact |
| candidate record | exactly `freeze.json schema.record_fields` (17 keys) | typed schema (next table), then every field except `null_reason` exact against the independent record |
| `summary.json` | `cells intervention_refines_auto n_cells n_candidate_records n_action_tables n_state_action_entries` | each row exact against the **independent** summary, never only against the cell copy; row identity is an int, unique and declared; the four counts exact against the declaration; `intervention_refines_auto` exact against the recomputed pairs |
| `fixtures/FX1_identity.json` | `fixture_id K transitions outputs stages alpha decoder macro representatives strict_rounds coarsening` | `fixture_id` is a str; `K` exact `max(alpha)+1`; frozen certificate |
| `seal.json` | `sha256` map | r2: hash per sealed file (bypassable only for semantic probes; absence never bypassed) |
| frozen identities | `freeze.json` groups | `isolated` and `run_files` resolve to the ORIGINAL run; `inputs` resolve to the current repository or an explicit `--inputs-root`, where the file set must also equal the declared set |

## Candidate record: typed schema

| field | type / shape / range | nullability |
|---|---|---|
| `record_id`, `cell_id`, `candidate_id` | int ≥ 0; `record_id = 1000·cell + candidate`, `candidate_id < n_candidates`, `cell_id` = declared cell | never |
| `candidate` | object of str keys with str/int values; exact against `study.candidates(n)[candidate_id]` | never |
| `K_candidate` | int in [1, N] | never |
| `decodable`, `closed`, `task_sufficient`, `is_control` | bool | never (`study.is_control` returns null only without a group count, which cannot occur here) |
| `decode_conflict` | state pair `[x, y]`, ints, 0 ≤ x < y < N | null **iff** `decodable` |
| `failing_actions` | strictly increasing ints in [0, n_actions) | never |
| `closure_witnesses` | map from a canonical decimal action-index string (< n_actions) to a state pair | never |
| `factors_through` | `true` | null **iff** not `task_sufficient` |
| `K_minus_Kstar` | int ≥ 0 | null iff not sufficient |
| `K_ratio` | `{num: int > 0, den: int > 0}`, exact reduced value | null iff not sufficient |
| `identical_to_optimum` | bool | null iff not sufficient |
| `null_reason` | non-empty str (free text, so not compared by value) | null **iff** `task_sufficient` |

Consistency between fields (for example `closed` ⇔ `failing_actions == []`, or
`closure_witnesses` keys = `failing_actions`) is enforced by the exact comparison with the
independent record. Conditional nullability is skipped when its controlling bool is
itself malformed; that bool is then already INVALID.

## Intentionally ignored, non-scientific

- `cost.json`, which holds timing (declared nondeterministic in `freeze.json`);
- `imports.json`, which holds provenance;
- the prose keys of `cases.json`.

All three are covered by the seal in normal mode only.
