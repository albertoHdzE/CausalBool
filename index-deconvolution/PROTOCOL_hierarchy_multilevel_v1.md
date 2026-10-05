# HID multilevel v1: bounded feasibility and ablation

Status: delegated development protocol, 2026-10-04. Executor: Claude Code.
Supervisor: Codex. Run ID: `multilevel-feasibility-v1-r1`.
Results: `results/hierarchy_multilevel_v1/multilevel-feasibility-v1-r1/`.

Read this file, `protocols/hierarchy_multilevel_v1/{SEARCH,BENCHMARK,ACCEPTANCE}.md`,
`contract.json`, `CASES.json`, `INITIAL_STATE.json`, and `DELEGATION_MANIFEST.json`.
The earlier `protocols/hierarchy_multilevel/CONCEPT_REVIEW.md` supplies rationale;
the new numbered contract supplies the executable scope. The JSON constants and
the numbered annexes must agree; an unresolved contradiction stops execution.

## 1. Scientific scope

Implement and evaluate reversible word abstraction at multiple word widths and
several levels, with exact phrase grammar and occurrence-gap proposals. Produce
an explicit width-by-level diagnostic map. This is exploratory development on
already exposed data, not prospective confirmation and not adoption of a new
default. No significance test, confidence interval, fractal-dimension estimate,
or causal-identification claim is an endpoint of this round.

Four components of the user's proposal are included now: multiple widths;
recursive dictionaries; occurrence/index analysis; and exact, costed hierarchical
explanations. “Gaps” has three separately recorded meanings in SEARCH section 5.
Adaptive allocation based on those diagnostics is a later isolated comparison;
do not silently add a tuned scheduler to this implementation.

Search-v2 remains inconclusive against its portfolio. V3a is an accepted harmful
comparison of k=4 with k=1, not a failed experiment and not the baseline to extend.
Use the accepted k=1 method. See its supervisory `REVIEW.md` under
`results/hierarchy_search_v3a/supervision/search-confirm-v3a-r1/`.

## 2. Ownership and preservation

You are not alone in this tree. Preserve all existing changes; do not reset,
stash, clean, restore from HEAD, commit, push, publish or create recurring tasks.
The user is independently editing notebook 19. Do not edit or execute it, its
builder, or any existing notebook. Read its saved section 3b only.

Create implementation only under `experiments/hierarchy_multilevel/`, with
`search.py` the single owner of the new algorithm and separate thin CLI,
record/report, and fixture/test adapters as needed. Import existing owners:
`hierarchy.model`, `wire`, independent `decode`, `candidates`, `ledger`, and
the unchanged `search_v2` k=1 entry point. Reuse owner watchdog machinery where
possible; any required parent/child persistence adapter belongs to this new
experimental package, not a copied search or codec engine.

Do not add files to or edit `hierarchy/`: its wildcard source closure is frozen
by older studies. Do not modify `src/`, existing experimental packages, old
protocols/results/ledgers, governance, root test configuration, dependencies, or
the packet. No production integration in this phase. If an existing API cannot
express the proposal, document the exact boundary and stop with a blocker;
do not change the grammar, wire format, old method registry or shared owners.

Other allowed new outputs: this run's result tree, `notebooks/build_21.py`, and
`notebooks/21_hierarchy_multilevel.ipynb`. These names are unoccupied at delegation;
if a new collision appears, stop rather than overwrite. Keep notebook README and
bitacora unchanged this round; the handoff supplies any proposed entry as text.

Verify packet and initial source hashes before edits. Capture hashes/status of
all existing hierarchy sources, shared imported owners, notebooks/builders and
old hierarchy result trees before execution and again at handoff. Concurrent
external drift is recorded separately, never silently restored. Scientific
dependency drift blocks a benchmark; unrelated user notebook drift does not.

## 3. Sequence and identity

1. Preflight and preservation; inspect owner APIs and publish the implementation
   map. `check_packet.py` must pass before edits.
2. Implement SEARCH and the required engineering fixtures. Ordinary coding fixes
   before the benchmark lock are authorized. Log every attempt and its time.
   Do not run exploratory corpus sweeps or alter this algorithm after seeing gains.
3. Pass fixture gates. Hash/archive the full executable dependency closure,
   tests, packet, resolved configurations, environment and analysis into a new
   `implementation_lock.json` and source snapshot. This is a reproducibility
   lock over exposed-data development, not a claim of blinded preregistration.
4. Run the fixed 96-case, four-arm feasibility design automatically. The baseline
   and augmentation jobs all run after this lock. No efficacy gate precedes the run.
5. Verify, report, execute the new artifact-only notebook under the reviewed
   guard from both working directories, write HANDOFF, and stop for review.

Resume only the same run/lock and validate all prior atomic records before
skipping work. A post-lock scientific code defect requires stopping, preserving
the failed run, and reporting the required amendment. Presentation-only fixes
may be separately hashed reporting revisions with retained failed evidence;
they must not change measured rows, computation code or endpoint arithmetic.

## 4. Finite resources

New allowance: 21,600 seconds (6 hours) automated/controller wall time, with
development 10,800; benchmark 7,200; reporting/verification 3,600. Charge setup,
tests, failures, idle running queues, resumes, reporting and handoff. No borrowing,
reset or reassignment. Keep all earlier studies' charges untouched.

Reserve the final 600 reporting seconds: 300 for final preservation/handoff and
300 for Codex review. At 3,000 reporting seconds stop optional verification;
at 3,300 stop executor work. Do not launch a job whose allowed maximum plus
checkpoint overhead exceeds the category's remaining allowance. Finish a truthful
partial handoff before a cap, without an autonomous continuation loop.

Each encoder/augmentation child: 30 s wall, 1 GiB RSS, at most two concurrent
children overall. Baseline and augmentation are separate children. A completed,
persisted baseline must survive augmentation timeout, RSS breach or crash.
Per augmented deployment the ceiling is baseline 30 s plus augmentation 30 s,
not a claimed 30 s total. Count workers and derived selection rows separately.

## 5. Later phases (not authorized by this packet)

M2: if engineering succeeds, use the recorded maps to specify one deterministic
gap-guided allocation policy and compare it to fixed allocation under matched
resource ceilings. Investigate dictionary-internal relations as a separate
addition. No tuning against a new confirmation set.

M3: freeze a selected complete method and test fresh held-out cases against k=1
and the nine-baseline portfolio. Address generalization and full deployment cost.

M4: test causal recovery under a specified observation/intervention model, with
known generating mechanisms or other identification assumptions and an explicit
mapping between levels. Test proposed self-similarity separately across scales,
origins and suitable controls. A grammar hierarchy by itself establishes neither
fractal dynamics nor causality. A static bit string does not supply a time axis.

Proceed through this round without routine approval questions. A negative result
is a finished phase. Return **ready for Codex review; not yet accepted**.
