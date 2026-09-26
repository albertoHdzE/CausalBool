# Paper foundation: direct-index compilation for the Luminal machine

Prepared by the lead, 2026-09-20. This is a writing contract and evidence map,
not a finished manuscript. Final implementation disposition is recorded in
`../results/direct_index_v4_optimization_repair2/REVIEW.md`.
The lead has recorded **ACCEPTED WITH LIMITATIONS**; drafting may begin.

## Working scope and title

**Direct Boolean Index Schemata for Scheduling and Scratch Allocation: A
Reproducible Luminal Compiler Case Study**

Present the representation, executable compiler, mathematical invariants,
validation, and measured quality/cost tradeoff. Do not frame these experiments
as a general complexity breakthrough or proof of asymptotic superiority.

## Claims supported by the implementation

1. A cube represented by an integer anchor and free-bit mask denotes a set of
   decision indices; exact intersections, differences and restrictions support
   scheduling/allocation queries without materializing the full assignment set.
2. Bootstrap obtains issue times and scratch addresses as minimum witnesses of
   direct-schema queries. It does not seed from the classical or serial compiler.
3. Joint queries encode bounded schedule/address neighborhoods and target
   criteria. Accepted witnesses are independently validated. UNSAT is local to
   those domains; resource exhaustion is UNKNOWN.
4. On the eight pinned public programs, the direct implementation's combined
   score is 2.008466202284657 versus 1.9013791212645499 for the frozen classical
   implementation. This is about 5.63% higher on that composite metric, not
   5.63% less execution time. Report cycles and scratch separately.
5. Optimizer-on/off must be reported separately. The public score gains already
   occur in bootstrap; joint optimization improves some generated cases.
6. Representation and reuse changes reduce this implementation's compile time
   relative to frozen v3. Use the final reviewed run's exact figures, intervals,
   source/export hashes and baseline, not the best result selected across runs.

## Evidence and limits

- Correctness: complete direct suite, unchanged 11-test public suite, 142-program
  acceptance corpus / 277 cases, standalone export and independent machine checks.
- Performance: 15 paired repetitions on eight public programs; separate frozen
  100-program evaluation corpus, five arms and three repetitions each.
- Source of final lead evidence:
  `../results/direct_index_v4_optimization_repair2/lead_review/`.
  Retain earlier rounds as repair history, not independent statistical samples.
- One machine and a fixed challenge corpus limit generalization. The generated
  evaluation set shares its generator with development inputs. Repeated timing
  measurements do not create additional independent programs.
- Within-run bootstrap intervals do not quantify between-run system variation.
  The classical timing changes on two public programs are unexplained; include
  per-program values and avoid diagnosing a cause without evidence.
- Direct compilation remains slower than the frozen classical implementation.
  Better output score and lower compile time are different objectives.
- The classical comparison is an implementation comparison. Its differing
  heuristics mean the score gain cannot be attributed solely to representation.
  Matched-heuristic ablations would be needed for that stronger causal claim.
- No global optimality, private-grader result, universal compression ratio,
  polynomial worst-case complexity, or general advantage over modern compiler
  optimizers has been established. Do not transfer the 1.2% representation figure
  from other challenges to Luminal.

## Manuscript structure and work before publication

1. Define the machine, objective, reference revision and scope of comparison.
2. Define cube semantics and prove the algebra and minimum-witness properties;
   distinguish mathematical proofs from exhaustive tests on small domains.
3. Specify bootstrap, joint constraints, deterministic ordering and budgets with
   pseudocode that corresponds to the accepted implementation.
4. Explain validation, frozen controls, corpus construction, timing boundaries,
   paired measurement design and failure handling.
5. Report per-program score components, both compilation modes, ablations,
   generated-case optimizer benefits, memory/resource cost and negative results.
6. Discuss related work and limitations. Verify primary literature before making
   novelty claims about cube covers, symbolic constraint processing, register
   allocation or scheduling; the vocabulary alone does not establish novelty.
7. Provide exact reproduction commands and an artifact manifest linked to the
   accepted source/export. Independently review proofs, citations, tables and
   scope before publication.

The manuscript may now be drafted around these bounded claims. Further attempts
to beat classical compilation time are not a
prerequisite for an honest empirical paper. Publication readiness and scientific
novelty remain separate questions from local implementation acceptance.

## Phase 2 structural-encoding feasibility (23 September 2026)

This is a separate campaign from an accepted isolated research implementation,
not a production compiler result or a new production benchmark. Its scientific
result is inconclusive. Authoritative evidence is
`../results/phase2_structural_encoding/phase2_repair_20260923c/`: `LEAD_ACCEPTANCE.md`,
`manifest.json`, `gates.json`, `hypotheses.json`, `checker.json`, `p0/summary.json`,
`p1/summary.json`, and the five raw files named by that P1 summary. The locked
design is in `../plan/phase2/PROTOCOL.json` and
`../plan/PHASE2_STRUCTURAL_ENCODING_PLAN.md`. The paper-local derivation is
`phase2_evidence.py`; generated values, source SHA256 values and raw-artifact
hash verification are retained in `generated/phase2_metrics.json`.

P0 passed its declared provenance/domain/oracle diagnostics. P1 is INCONCLUSIVE:
its fixed streams retained 160,000 attempts, 819 completed draws and 1,356 case
checks with zero observed discrepancies, but four of eight public programs fell
below the required 100 distinct completions. All raw-bit streams produced zero
completions. P2-P5 are BLOCKED_BY_GATE and unmeasured. The checker found zero
findings and internally consistent retained artifacts, while
`artifacts_complete=false` and `scientific_success=false` remain explicit. These
are finite-fixture checks, sampled executions and checker results with different
denominators; zero observed defects is not a general proof. No compression,
scaling, discovery or performance benefit is established. A new sampling policy
requires a separate protocol amendment and fresh evidence.

The 113 MB raw-attempt file remains local because repository packaging is
unresolved. This evidence is not portable, published or fully archived. The
accepted production measurements and September 20 tests remain separate from
the September 23 Phase 2 campaign.
