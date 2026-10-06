# Decision -- task-compaction-v1 final audit closure (audit revision r4)

**Recommendation: V1_READY_FOR_SUPERVISOR.** Executor recommendation only; supervisor
acceptance is not claimed.

R1 and R2 are closed in a separately identified wrapper, `src/audit_r4.py`, which loads the
hash-pinned r3 and replaces exactly two of its entry points (`check_fixture`, `R2.check_seal`)
plus its report finisher (to stamp the r4 identity). No scientific code is duplicated: the
encoder, model, minimizer, production pipeline, expected-value authority `expected_r3.py`, and
the frozen certificate primitives are all reached through r3's verified import graph.

- **R1.** FX1 is bound to its declaration (`fixture_id` "FX1_identity", outputs [0,0,1,1],
  transitions [[0,1,2,3]]); all eleven fields are checked for type, shape, range and
  nullability; every rejected branch writes a field-specific INVALID issue; an absent file is
  INCOMPLETE; `fixture_FX1` always reports intended 1, availability, schema validity and the
  number of completed certificate checks. The valid-but-not-minimal COR3 case still yields
  validity True, minimality False.
- **R2.** The 60 intended paths and hashes come from the original seal, pinned by SHA-256 and
  cross-checked against the separately pinned original output manifest (all 60 values). The
  candidate seal never defines coverage; data bytes are compared with the authority. Missing
  seal or entries are INCOMPLETE in both modes; undeclared, malformed or contradicting entries
  are INVALID in both modes; byte mismatches are INVALID in normal mode and only they are
  bypassable.

Evidence: 73/73 cases as required (52 inherited + 21 new); r3 accepts all six review-style
copies as VALID_COMPLETE where r4 does not; 7/7 restored-fault mutants caught with the case's
own fragment absent; 29 run-local tests; 125 active tests and doc examples; ruff clean; two r4
runs byte-identical; every scientific key and every shared count equal to the saved r3 audit
(24 cells, 3,276 candidate decisions, 85,504 transition entries); preservation scan 110,713
files unchanged; five active paths and the three old output manifests unchanged.

Not claimed: full CI (`make ci-local` was not run, by instruction), repository guards, vendor
parity, and any new scientific result.
