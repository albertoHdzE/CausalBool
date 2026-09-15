# CausalBool arithmetic compiler — Luna implementation handoff

## Objective and status

Status: PLANNED; no worker assigned and no implementation accepted.
Prepared against commit `ba4983ad52ffe45d47a19938338e026c5259b48f`.
Implementation owner: Luna. Review, integration, corrections and acceptance:
the returning lead assistant. Worker completion means submission for review.

Deliver an additive, executable route from CausalBool Boolean circuits to the
existing quadratic-constraint representation. Demonstrate genuine engine reuse
on Q5 (64-bit range), Q6 (field-element exclusion of one), and a bounded Q7
factor-verification circuit. Measure its costs against the existing arithmetic
builders. The purpose is useful application of the implementation, not merely
renaming existing arithmetic code or increasing the paper's attribution count.

This plan does not reopen the completed v1 task list. Keep its STATE.json,
release evidence and manifest as historical records. Record new work separately.
The author's subsequently requested AI disclosure supersedes the old MASTER.md
restriction on AI attribution; preserve the approved disclosure.

## Read before implementation

- `plan/MASTER.md`: challenge definitions, field, original acceptance contracts.
- `src/oxparc_challenge/{boolean,symbolic,constraints,row_evaluator,circom,gadgets}.py`.
- `index-deconvolution/src/{causalbool,deconvolution}.py` (repository-relative).
- `doppel-challenge/src/doppel_challenge/repertoire_program.py`.
- `tools/paper_index_examples.py`, and existing discrete, rows and gadget tests.
- Applicable AGENTS.md instructions and the current worktree diff.

Repository facts to preserve:

1. Q2 already uses `causalbool.apply_gate`, the shared decision manager, and
   `essential_variables`/`reduce_column`. Other challenge solution modules
   currently use dedicated arithmetic/vector code.
2. The inverse implementation actually stores `reduced_truth_table` and calls
   `reduce_column`. Whole-system interpretation does not erase that operation.
   Prepare a precise manuscript correction; do not silently change the engine
   to fit the current prose or deny the mathematical operation.
3. Gate evaluation, deconvolution, symbolic equivalence, and constraint
   compilation are distinct contributions. Report separately which is used.
4. Full-adder smoke check already passed all eight inputs using existing XOR
   and MAJORITY gates and deconvolution replay. Reproduce it as durable evidence;
   it is not evidence of a completed multiplier or target-size solution.

## Scope and ownership

First implementation milestone: Q5, Q6, and small Q7. Q8 receives a feasibility
assessment only. Q1, Q3, Q4 and the existing Q2 implementation remain baseline
comparators; no new claim of using CausalBool to solve them is authorized here.

Prefer additive files under:

- `src/oxparc_challenge/boolean_arithmetic.py`: general acyclic bit circuits,
  evaluation adapter, arithmetic builders and witness tracing.
- `src/oxparc_challenge/boolean_constraints.py`: compiler and scalar bindings.
- `tests/test_boolean_arithmetic.py`, `tests/test_boolean_constraints.py`.
- `tools/verify_boolean_arithmetic.py`: reproducible evidence entry point.
- `evidence/causalbool_arithmetic/`: small reports, hashes and measurements.
- `plan/causalbool_arithmetic/`: CONTRACT.md, STATUS.json, LUNA_REPORT.md,
  MANUSCRIPT_PROPOSAL.md and LEAD_REVIEW.md.

Preserve the MAJ3-only BooleanCircuit contract. Do not broaden it in place.
Reuse the existing constraint serializer, row evaluator and Circom exporter.
Do not modify legacy gate semantics, legacy fixtures or acceptance thresholds.
Propose necessary shared-interface changes explicitly in the handoff.
Keep unpublished manuscript changes in MANUSCRIPT_PROPOSAL.md until lead review.

## Implementation stages

### L0 — Freeze the executable contract

Record base commit and dirty files. Use an isolated worktree/branch when
implementation starts; preserve existing user edits. Record actual worker model
identity. If Luna is unavailable, report that fact; do not substitute silently.

Specify ordered input and gate references, duplicate ports, fan-out, constants,
selected output wires, bit order, scalar binding, public/private signals and
failure behaviour. Use a combinational DAG evaluator; one synchronous Network
step is not evaluation of an entire multilevel combinational circuit.

Start with AND, OR, XOR, NOT, MAJORITY of three inputs and constants. Unsupported
gates fail explicitly. Gate execution must call the existing CausalBool engine.
Publish a short soundness/completeness argument for every supported lowering.

### L1 — Compile gates into quadratic rows

All rows obey A(w)*B(w)=C(w) over the field specified in MASTER.md.
Examples: AND ab=z; OR ab=a+b-z; XOR 2ab=a+b-z; NOT a+z=1.
Lower MAJ3 through proved Boolean identities and explicit auxiliary wires.
Enforce input bitness, constant values, output acceptance and every scalar
binding. Prove internal bitness inductively or constrain it explicitly.

Witness generation and constraint enforcement are separate. A witness helper's
refusal does not demonstrate rejection by the constraints. Preserve a mapping
from original gates to rows and auxiliary signals for diagnosis and review.
Serialization must be deterministic and resource limits explicit.

Acceptance: exhaustive local gate relations, including repeated operands and
constants; independent replay; malformed references and cycles rejected;
nonbinary external assignments and forged internal wires rejected by rows.

### L2 — Q5 and Q6 end to end

Q5: bind a field scalar x to 64 Boolean wires using x=sum(2^i*b_i).
Prove that the represented integer is below the field modulus and that every
64-bit integer has a witness. Explain honestly how much is Boolean semantics
versus the scalar-binding compiler; do not invent a nontrivial inverse step.

Q6: support the original domain of canonical field elements, not just 64 bits.
Use enough bits for P, enforce the represented integer <P, bind it to r, and
require the Boolean comparison r!=1. Without the <P condition, the encoding
P+1 could satisfy the scalar binding for r=1 and invalidate exclusion.
Compare with the existing single inverse constraint; expect extra cost.

Acceptance: 0, 1, upper boundaries and invalid bounds; forged decompositions;
Q6 noncanonical aliases including P+1 where representable. Submit invalid
assignments to the serialized rows, not only to the witness constructor.
Compile the new systems with the existing Circom path and verify exported
compiled rows and valid/invalid witnesses. Missing tooling is UNKNOWN.

### L3 — Small Q7 multiplier and acceptance predicate

Build multiplication from CausalBool gates, including partial products and full
adders. Keep the full 2w-bit product before enforcing the original w-bit public
product and zero upper bits. Require both factors >=2. A truncated multiplier
must never accept an overflowing product modulo 2^w.

Default exhaustive case: w=4, all factors and all public n (4096 triples).
Use independent integer multiplication/comparison as oracle. Include 4*4 with
n=0 as a truncation attack, swapped factors, zero/unit factors, altered public
product, and corrupted sum/carry wires. Demonstrate one deliberately defective
local block and an exact counterexample found by the behavioural comparison.

Run deconvolution on bounded local block repertoires (full adder and selected
small blocks), recover named rules where possible, and replay all local states.
Keep this out of the correctness trust boundary: independently prove compiler
composition. A local replay does not prove the whole multiplier or provide a
minimum circuit. Avoid calling an LUT replay a discovery of a generative rule.

Q7 target width is 64. A four-bit demonstration must be labelled partial Q7.
Attempt larger widths only after bounded acceptance passes, with explicit limits
and separate results. Do not claim the target implementation unless built and
verified at that width; distinguish sampled tests from universal proof.

### L4 — Comparison and submission

Measure gates, auxiliary signals, quadratic rows, serialized bytes, build and
witness time, and compiled rows where available. Compare like-for-like domains
and public/private contracts with current Q5/Q6/Q7 builders. If a comparable
small baseline is needed, implement it separately and identify it as new.
Do not compare a four-bit circuit with a 64-bit baseline as an efficiency win.

For Q8, give a composition/scaling assessment: which verified local components
can be reused, what 4096-bit support would require, and where resource limits
are likely. Report estimates separately from measurements. No target-size
enumeration, factoring-performance claim or zero-knowledge proof claim follows
from compiling a factor-verification relation.

Suggested default limits: one heavy process at a time, 300 seconds per bounded
check, 600 seconds per Circom compile, 2 million decision nodes. Respect stricter
environment limits; resource exhaustion is UNKNOWN, never PASS. Do not start
unbounded sweeps or change limits globally to obtain a passing result.

## Required submission and evidence

STATUS.json records each stage as planned, running, submitted, changes_requested
or accepted, with dependency and blocker fields. Only the lead sets accepted.
LUNA_REPORT.md includes:

- base/head commits, actual model identity, all changed files and rationale;
- exact commands, exit codes, environment, test counts and resource outcomes;
- per-question coverage: existing reuse, new code, mathematical proof, finite
  checks, target coverage and remaining work;
- hashes of relevant sources/artifacts, PASS/FAIL/UNKNOWN per acceptance item;
- all failures, skipped checks, unexecuted checks and suspected limitations;
- cost comparisons and a concrete reviewer reproduction command;
- manuscript proposals limited to supported claims, including the correction
  concerning reduced tables and a precise contribution statement.

Keep the evidence reproducible and small; exclude build caches and bulky
compiler intermediates. Do not alter historical release PASS records to imply
that the new approach was already covered by them.

## Returning lead's mandatory review

1. Inspect source and dependency paths: genuine CausalBool calls, preserved
   old interfaces, no circular verification or renamed arithmetic baseline.
2. Review proofs of Boolean lowering, scalar bindings, Q6 canonical encoding,
   Q7 product width and factor exclusions. Check both soundness and completeness.
3. Independently run the bounded suite and challenge regressions affected by
   the changes. Exercise forged witnesses against serialized and compiled rows.
4. Add reviewer-selected counterexamples, especially aliasing, missing bitness,
   truncation and disconnected/duplicate wires. Do not accept solely from Luna's
   own tests or summary.
5. Recompute attribution and performance conclusions from actual artifacts.
   Determine whether the outcome is a full answer, partial support, or a probe.
6. Fix localized issues directly; return architectural/proof failures to Luna
   with concrete reproduction cases. Revalidate every correction.
7. Write LEAD_REVIEW.md with accepted/rejected items and unresolved limits.
   Only then integrate scientifically justified manuscript changes, rebuild
   relevant PDFs and refresh edition evidence. Avoid gratuitous regeneration
   of unchanged figures. Preserve author edits and the AI disclosure.

Completion requires all first-milestone acceptance items and lead review.
Publishing, pushing or merging is a separate action, not worker acceptance.

## Ready-to-use Luna instruction

Implement stages L0–L4 of
`0xPARC-challenge/plan/CAUSALBOOL_ARITHMETIC_LUNA.md` in order. Treat this as an
additive implementation milestone, preserving the completed challenge baseline.
Use existing CausalBool execution and bounded deconvolution explicitly. Deliver
the compiler, Q5/Q6 demonstrations, small-Q7 demonstration, adversarial checks,
cost evidence and LUNA_REPORT.md. Submit for lead review; do not self-accept or
edit published manuscript claims. If a prerequisite fails, report its exact
cause and continue independent in-scope work where possible.
