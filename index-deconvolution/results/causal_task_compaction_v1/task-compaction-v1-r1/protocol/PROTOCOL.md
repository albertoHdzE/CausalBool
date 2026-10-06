# Task-preserving causal state compaction — task-compaction-v1-r1

Status: executable delegation, activated by the user forwarding NEXT_CLAUDE.md. Codex has written declarations only; no new model computation or implementation was run while preparing this packet. This authorizes the complete bounded engineering and exact finite-model study below. It does not authorize a successor experiment, active-source integration, commits or publication.

## 1. Question and contribution

For a named observable h and a declared set Q of deterministic interventions, what is the smallest deterministic state grouping that preserves h now and after every finite sequence of actions in Q?

Implement the established partition-refinement construction in the existing deconvolution owner, in an isolated source revision. Use it as an exact reference against the earlier fixed-width, multi-width and nested candidate family. The contribution of this phase is a verified capability and a finite-model comparison, not a new minimization theorem or identification algorithm. Read THEORY_AND_FIXTURES.md before implementation. Known literature is justification for this engineering implementation, not a novelty stop rule.

Prior conclusions stand: k=1 remains the accepted compression reference; the tested multilevel/dictionary additions gave no retained archive gain; the gap ranking is not promoted. None is tuned or rerun here. This phase concerns state cardinality and task preservation, not bits in a decodable archive.

## 2. Fixed task population

Use the accepted M1–M4 model definitions and LSB-first convention from the manifest's MODEL_AND_MAPS.md and adopted source-r2/study.py. State domain is the ENTIRE X={0,...,2^n-1}; n=8,8,8,10 respectively. No initial-state restriction or reachable-state pruning.

Three observables, fixed for every model:

- T0: h(x)=x & 1, the first coordinate.
- T1: h(x)=(x>>(n-1)) & 1, the last coordinate.
- TP: h(x)=popcount(x) mod 2, a distributed readout across all coordinates.

These are engineering readouts, not biological targets. They deliberately span two coordinate locations and one nonlocal grouping without selecting tasks after results. All are nonconstant on the declared full state space.

Only tau=1 is studied. Two action regimes:

- AUTO: Q=[id], where T_id=F, NOT the identity function on states.
- INTERVENTION: exactly study.track_d_q(n), in its existing order: id, 2n boundary resets, n boundary flips, 2n mechanism replacements, tick. T_q=study.Model.q_table(q,1). Thus reset/flip acts BEFORE the update, knockout replaces the node's update for that step, and tick performs F^2.

An action is chosen at each decision boundary and its complete T_q is applied before observing the next state. A knockout lasts for that action's step; it is not silently persistent across subsequent actions. Tick counts as one action of duration two micro steps. Compare action depth, not uniform physical time. All actions are admissible at every state. Keep every original action ID even if two transition tables coincide. No coarse beta or inferred action equivalence.

There are 24 cells: four models x three tasks x two regimes, ordered model M1..M4, task T0,T1,TP, regime AUTO,INTERVENTION. IDs 0..23 as in CASES.json. Twelve INTERVENTION cells are the main engineering population; twelve AUTO cells are controls. No statistical population inference or bootstrap.

Generate and store each model's action tables once; reuse across tasks. AUTO is the id subtable. The full sets contain 178 action tables and 85,504 state/action entries (3*42*256+52*1024). Old results_d.jsonl is NOT an input to this phase; historical labels are unnecessary. This makes the new computation independent of the previous large untracked label artifact.

## 3. Exact construction and outputs

Let P0=canonical_partition(h). Iteratively set

    P[d+1](x) = canonical_partition((P[d](x), tuple(P[d](Tq(x)) for q in Q)))

where canonical labels follow first appearance over x ascending, and Q order is frozen. Every step refines the preceding partition; no block merges. Stop only at equality of canonical label vectors. Save P0 through the first repeated stable vector, with round IDs. The stable partition alpha* is the coarsest output-preserving congruence on all X. Prove this in THEORY.md as directed in THEORY_AND_FIXTURES.md; do not infer minimality merely from zero commutation failures.

For every cell save alpha*, all stage vectors, representatives (smallest x per block), decoder H with H(alpha*(x))=h(x), and complete G_q satisfying G_q(alpha*(x))=alpha*(T_q(x)). Verify output equality for every state and commutation for every state/action pair using the accepted owner. Return no success for truncated data or premature stopping.

Primary per-cell measurements: |X|, K0=|h(X)|, K*=|alpha*(X)|, K*/|X| as an exact fraction, n-ceil(log2 K*) integer state-capacity saving, and strict refinement rounds. K*=1 gives capacity zero but is impossible for these nonconstant primary tasks and is a harness failure there. These capacity numbers exclude decoder, transition-table, action-label and state-to-grouping storage. They are NOT archive compression or total memory/runtime savings. Report those table entry counts separately, not as an invented bit code.

Depth d has a precise meaning: Pd distinguishes outputs following words of at most d actions, including the empty word. Nested partitions are prediction-horizon refinements, not automatically spatial scales, discovered grammar or fractality. Save explicit coarsening maps Pd+1 -> Pd. Do not call the first stable depth the maximum shortest-witness length without stating the indexing convention.

For each strict refinement round, select the lexicographically first pair x<y that was equal in Pd but differs in Pd+1. Deliver one shortest distinguishing action word, ties by Q order, using the saved refinement certificate recursively. If h(x)!=h(y), the witness is the empty word. Replay all witnesses from both states against the original action tables, and record outputs along the full path. One witness per round is an explanation, not the proof of minimality for every pair; the complete refinement certificate supplies that proof.

## 4. Compare the user's word and nesting proposals with the exact reference

Use ALL original study.candidates(n), including controls and duplicate partitions: 135 for M1–M3, 141 for M4. Canonicalize alpha_value over every state. Across 24 cells this gives 3,276 candidate/task/regime records. Cache candidate vectors and closure checks by model/regime; task decoding differs by task. This is a new task-specific comparison at tau=1, not a rerun or revision of the historical V/D/X study.

For each candidate alpha independently record:

1. Output decodability: does alpha determine h? If not, retain the smallest conflicting state pair.
2. Transition closure: for EVERY declared q, does alpha determine alpha after T_q? Retain failing action IDs and the smallest witness per failing action. Evaluate closure even when output decodability fails; do not conflate failure types.
3. TASK_SUFFICIENT iff both checks pass. For those rows, verify alpha* factors through alpha on all states. K_candidate >= K* must hold; a violation is a harness/theory defect. Save exact K_candidate-K* and K_candidate/K*, and whether the partitions are identical up to labels. For failing rows these comparison fields are null, with reasons.

Baselines are identity (always sufficient, K=|X|), the output partition P0 (may lack closure), and alpha*. Constant controls fail decoding for these three tasks. Report the smallest sufficient old candidate, with ties by ascending candidate ID; identity guarantees availability. Also report lossless-control-excluded best, null if none. Preserve raw counts AND distinct-partition counts so duplicates are not discoveries. Do not relabel historical FULL results; task sufficiency is a new property.

F1/F3 compare widths 2,3,4 and offsets; F4 covers analyst-imposed nesting. Equality of an F4 partition to an F1 partition is representational duplication, not an additional explanatory level. Gap scores are not used to generate, rank or select anything in this phase. A shorter state description does not establish a grammar or a shorter archive.

## 5. Gates, development and freeze

Start with manifest verification and the preservation snapshot BEFORE writing development files. Stop on output-directory collision or changed scientific input identity. Output is results/causal_task_compaction_v1/task-compaction-v1-r1/ under index-deconvolution.

Read OWNERSHIP.md; approved ownership is an additive extension to an isolated copy of src/deconvolution.py, not a new algorithm package. No active-source changes. Declare all hand fixtures and expected outcomes in fixtures.json before the first execution. Implement, run fixture/regression tests, and kill all six specified mutants before locking sources. Production inputs may be parsed and hashed before the lock, but do not run the new minimizer or candidate comparison on M1–M4 before the lock. Small declared controls use separately constructed fixture tables.

Read Knuutila §§2.2–3.1 in the primary paper; record exact sections read and the model mapping. If it cannot be obtained, use a verified original primary source for the same construction and record the substitution BEFORE freeze. Literature similarity does not block this explicitly authorized engineering work. A mathematical contradiction in the contract DOES block execution; hand off a concrete counterexample rather than silently changing the question.

Freeze protocol, cases, fixtures, core revision, orchestration, audit, tests, import identities and input hashes before the first 24-cell execution. Predeclare the result schema and expected ID sets. Perform one production run. No change to tasks, Q, full domain, output timing, ties, algorithm or tests after scientific outcomes are inspected under this run ID. A defect in scientific computation yields FAILED_RUN and handoff with partial evidence; no tuned retry. Presentation-only repairs must be separately identified, retain failed attempts, and cannot alter measured fields.

Evidence labels: observed inconsistency => INVALID; otherwise missing required evidence => INCOMPLETE; otherwise VALID_COMPLETE. If both are present, INVALID wins. A candidate's demonstrated inability to preserve a task is an ordinary valid negative outcome, not invalid evidence. Do not replace missing values with zero. A timeout is missing work, not a negative scientific result.

## 6. Verification and independent audit

Run the 73 accepted core/study regression tests against the isolated adopted extension, plus the newly declared fixtures. No need to rerun unrelated compression studies or Track G's dependency tests. Lint new/changed Python files. Run applicable repository guards read-only and report pre-existing failures accurately; do not repair unrelated sites. Do not run make ci-local if it rewrites unrelated work; record the scoped substitute without claiming full CI passed.

The audit imports no minimizer, witness helper, producer comparator or report computations. It may use the accepted model owners and existing candidate declarations. It must:

- Check all source/input hashes, exact 24/3,276 ID sets, table dimensions, action IDs and state ranges BEFORE computations. Inspect available evidence even if another record is missing, so invalid outranks missing. Return structured results for absent or malformed evidence, not KeyErrors.
- Validate all 85,504 transition entries against the accepted owners; independently hand-check counter transitions and the declared rule-150 fixture. Trusted owner agreement is not claimed to be an independent rederivation of every model.
- Verify each P0 against h and every subsequent saved partition is EXACTLY the equivalence induced by the previous labels and successor labels. Implement this separately with per-block grouping and two-way signature/label consistency, not an import or copy of the producer refinement routine. Verify strict refinement until the last equality. This certificate plus the reviewed theorem proves minimality; arbitrary stable finer partitions must fail this audit.
- Directly check every decoder value and macro transition, every coarsening map, every witness replay and its minimal depth using the stage at which its pair first separates. A witness must act in the written order. Check all candidate sufficiency decisions from saved alpha and tables, every failed witness and every optimum comparison.
- Check primary counts, exact fractions, null handling and all reported numbers/tables, including the best-candidate selections. Across each task, INTERVENTION must refine AUTO; K cannot decrease when actions are added. This is an implication of the contract, not an empirical hypothesis.

Four artifact corruptions on copies: change a decoder value; change one G_q entry; replace a minimal certificate by a stable identity partition in the 4-state identity fixture (validity passes but minimality must fail); remove one cell while corrupting another (INVALID must outrank missing, with both recorded). Verify relevant scientific assertions, not only a broken file hash. Use separately manifested corruption copies and explicitly bypass their integrity rejection solely for these semantic probes. Original artifacts remain untouched.

One command must reproduce all deterministic scientific outputs in a fresh directory from delivered sources. Freeze/cost/time/preservation records need not be byte-identical; specify the exact deterministic artifact list before reproduction. No destination overwrite. Review outputs are marked ready for Codex review; not yet accepted.

## 7. Deliverables and stop rules

Deliver HANDOFF.md, REPORT.md, DECISION.md, THEORY.md, claim-to-evidence table, sources/sections-read record, protocol/fixtures/cases snapshots, dependency/import provenance, isolated core revision and unapplied integration patch, all scientific artifacts/certificates/witnesses/candidate comparisons, independent audit and corruption results, tests/mutation logs, attempts and time ledgers, preservation before/after, manifests, and reproducibility command. Save per-case files or deterministic shards below 10 MB; do not discard witnesses to meet that limit. No commits, uploads or publication.

Provide one artifact-only worked example per model: use TP/INTERVENTION, show h, K0, K*, a refinement witness if one exists (otherwise explain stability), and best old candidate comparison. Include a small diagram/table of the refinement chain from saved artifacts. Do not cherry-pick the best task. A notebook inside the run is optional, but must import no model/minimizer code and write no evidence; do not edit existing notebooks or their index.

Report separate per-cell outcomes: EXACT_REDUCTION (K*<|X|) or NO_REDUCTION (K*=|X|), only for valid complete cells. Compare the old family with the optimum as MATCHES_OPTIMUM or CANDIDATE_GAP; never infer that a gap implies archive savings. Summaries are counts, not a global GO/HARMFUL verdict. No numerical reduction is required for a successful engineering phase.

Fresh executor budget 6,600 wall-clock seconds: preflight/literature/proof 900; implementation/fixtures/tests/mutations 1,800; production 900; independent audit/corruptions 1,200; reporting 900; reproduction/preservation/handoff 900. Separate Codex reserve 600; total 7,200. Include failed attempts and overhead; no category transfers. At 80% of a category stop optional work; retain enough of its allocation for a truthful handoff. At any cap stop and report incomplete work. No schedules, recurring loops, background continuation or automatic next phase.

Decision for the next review will concern correctness, integration readiness and what the exact task limits imply. Even positive results do not authorize scaling, noise models, new tasks or a general theory claim without a separate justified protocol.
