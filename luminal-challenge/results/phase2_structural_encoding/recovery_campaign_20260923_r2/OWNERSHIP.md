# Ownership record for the phase 2 research system

Written before the code, as the repository's single-owner law requires: locate
the owner first, never after.

## Q1 -- where does the core of each concept live?

| Concept | Owner | This package |
|---|---|---|
| Hardware semantics, independent acceptance | `.reference/machine.py` (pinned) | imported, never restated |
| Derived program facts, lifetimes, assembly, footprint, lower bounds | `direct_contract.py` | imported |
| Cubes, exact set algebra, budgets and meters | `schema_index.py` | imported |
| The absolute-field joint query | `direct_constraints.py` | used unchanged as a control |
| Accepted target and window policy | `direct_optimizer.targets_for`, `windows_for` | called, not copied |
| Accepted compiler, its bootstrap and its limits | `direct_compiler.py` | called, not copied |
| Corpus generation | `tests_direct/generate_programs.additional_program` | called, not copied |
| Peak RSS conversion, file digests | `compare_direct.py` | imported |
| Production source list | `verify_direct.SOURCES` | imported |

New owners created here, each with one responsibility:

| Owner | Responsibility |
|---|---|
| `research/structural_encoding.py` | Domain, fixed layout, options, encode/decode, all four codecs, canonical JSON |
| `research/structural_search.py` | DFS traversal, admissible bounds, acceptance policy |
| `research/structural_models.py` | Cover merge, byte format, proposal policies |
| `research/structural_oracle.py` | Independent enumeration and hidden evaluation |
| `research/run_structural_experiments.py` | CLI, harness, corpora, P0-P5 orchestration |
| `research/check_structural_evidence.py` | Independent artifact checks and gate recomputation |

Owners added by the 2026-09-23 lead repair, each because the checker needed to
recompute a number the runner had produced inline. The rule applied was
enrich-the-owner: the computation moved into one named function in the module
that already owned the stage, and the checker now calls that function on the
*raw rows* instead of holding a second copy of the statistic.

| Owner | Responsibility | Called by |
|---|---|---|
| `run_structural_experiments.AttemptSink` | Streams one raw JSONL row per sampling attempt | `stage_p1` |
| `run_structural_experiments.control_serialisation` | The P3 control covers and their median | `stage_p3`, the checker |
| `run_structural_experiments.p4_contrasts` | The P4 contrasts, H4 bounds and advancement flag | `stage_p4`, the checker |
| `run_structural_experiments._model_optimise` | The conditional half-search/half-model arm | `structural_optimise` |
| `structural_models.ordered_union` | Lazy ascending distinct members of a cube union | `cover_members`, `proposals` |

`cover_members` became the eager form of `ordered_union` rather than a second
traversal, so the exact-cover equality check and the lazy proposal stream cannot
disagree about what a cover denotes.

## Q2 -- does each concept already exist under another name?

Searched by body fragment and by behaviour, not by name.

* *Bundles to issue cycles.* Three test modules and `common.py` each inline the
  same comprehension. The owner that also validates it is
  `machine._collect_issue_cycles`; `structural_encoding.issue_cycles_of` calls
  that one rather than making a fifth copy. `common.py` is a declared exception
  and is barred from the production path, so it is not a candidate owner.
* *Cube algebra.* `schema_index` owns it. Nothing here defines `Cube`,
  `intersect`, `difference` or a cover normaliser.
* *Budgets and deadlines.* `schema_index.Budget`/`Meter` own budgeted work with
  a deadline; the decoder and the search charge against them instead of
  inventing a second meter.
* *Paired bootstrap.* `benchmark_optimization.paired_bootstrap` resamples
  repetition identifiers within a fixed suite. Phase 2's primary interval
  resamples *programs within family with families weighted equally*, which is a
  different estimand over a different sampling unit. They are two statistics,
  so they keep two names and both are reported; neither replaces the other.
* *Lower bounds on C and S.* `direct_contract` owns
  `cycle_lower_bound`, `memory_lower_bound`; `structural_search` composes them
  with prefix information rather than restating them.

## Q3 -- why is a new owner needed rather than enriching an existing one?

Because the contract makes this an *isolated research path* that must not change
production. Enriching `direct_compiler` or `direct_constraints` would put
research code inside the accepted compiler's dependency graph and inside the
release contract. The new owners depend on the production owners; no production
owner depends on them, and `export_direct.py` is unchanged.

The independent oracle is the one place where sharing is forbidden in the other
direction: it may not import the codec, the search or the derived legality
checker, because its whole value is deciding membership by a path that shares no
feasibility predicate with the candidate.

## Q4 -- what executable guard keeps each owner single?

`research/check_structural_evidence.py --architecture` runs in the same commit:

1. an AST scan of `research/` for a second definition of a machine constant, a
   cube type or a cover operation;
2. an import-boundary check that the oracle's module graph excludes
   `research.structural_encoding`, `research.structural_search`,
   `research.structural_models` and `direct_contract`, evaluated at run time in
   a subprocess rather than read off the source;
3. planted-copy and planted-import fixtures, which the guard must reject while
   the unmutated control passes.

The AST scan is supporting evidence with a stated limit: it detects a duplicate
*definition*, not a semantically equivalent reimplementation spelled differently.
The runtime import check is what closes the oracle boundary.
