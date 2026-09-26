# Blocker: the four required new test modules fail a frozen production gate

Status: **unresolved by the implementer, by contract.** Handed to Codex.
Raised: 2026-09-22. Run: `results/phase2_structural_encoding/phase2_20260922_final`.

## The contradiction

Two clauses of the implementation contract cannot both be satisfied, and neither
is in my authority to relax.

* **Section 2** fixes the allowlist of new files. Four of them are
  `tests_direct/test_phase2_encoding.py`, `tests_direct/test_phase2_search.py`,
  `tests_direct/test_phase2_models.py` and `tests_direct/test_phase2_evidence.py`.
  The paths are given, not chosen.
* **Section 8** requires `python3 verify_direct.py --stage all` to run. Its
  `evidence` stage runs `tests_direct/test_evidence_checker.py`, which exercises
  the frozen `check_optimization_evidence.py`.

`check_optimization_evidence.Checker.check_recorded_hashes`, at
`check_optimization_evidence.py:312`, computes

    required_tests = {path.name for path in sorted((ROOT / "tests_direct").glob("*.py"))}

and requires every discovered file to appear in a **historical** provenance
record. That record, `results/direct_index_v4_optimization_repair2/final/provenance.json`,
lists the eleven test modules that existed when the accepted optimisation
campaign ran. The four new modules cannot be in it.

## Measured effect

| Condition | `tests_direct.test_evidence_checker` | `verify_direct.py --stage all` |
|---|---|---|
| Four new modules present | 2 of 64 fail | `evidence: FAIL`, `overall: FAIL (1 failing)` |
| Four new modules moved aside | 64 of 64 pass | not re-run; the evidence stage is the only failing one |

Both failures are the same check, `recorded_hashes:final`, with the same reason:

    missing tests: ['test_phase2_encoding.py', 'test_phase2_evidence.py',
                    'test_phase2_models.py', 'test_phase2_search.py']

Recomputed independently against the working tree at this run's HEAD:

* recorded source hashes differing from disk: **0** (`source drift: []`);
* recorded test hashes differing from disk: **0**;
* missing sources: **none**;
* missing tests: the four above, and only those.

So no production source has drifted. The gate fails solely because it
*discovers* test files by glob while comparing them against a frozen list.

Every other stage of `verify_direct.py --stage all` passed at this HEAD:
schema 65, contract 31, constraints 43, construction 22, optimizer 22,
independence 13, export 33, benchmark 47, acceptance/corpus 142 programs,
acceptance/public_suite 11, acceptance/cli. The unchanged
`compare_direct.py --repeats 3 --timeout 20` passed all seven of its gates with
a combined direct-index score of 2.008466202284657, identical to the accepted
historical value.

## Why I did not resolve it

Each available repair is forbidden to me.

1. **Edit `check_optimization_evidence.py`** so the glob excludes phase 2 files.
   It is protected source under section 2 and hash-locked in `BASELINE_LOCK.json`.
   Section 8 also says "Do not edit protected source to test failure."
2. **Add the four hashes to the historical provenance record.** It is accepted
   evidence under section 2, and "No historical result directory may be a
   command's output destination."
3. **Move the four test modules elsewhere.** Section 2 fixes their paths, and a
   file outside `tests_direct/` would not be discovered by the declared unit
   command in section 8 either.
4. **Regenerate the provenance by re-running the accepted campaign.** That
   would overwrite accepted evidence and is outside this assignment's scope.

Contract section 1: "A contradiction between these is a blocker to the affected
task: retain evidence and hand it to Codex. It is not permission to choose a
more convenient interpretation."

## What a lead decision would need to choose between

Stated for convenience only; the choice is Codex's, not mine.

* Amend `check_optimization_evidence.py` so the required-test set is *declared*
  rather than globbed, in the manner of the sibling repository's
  `MANIFEST.tsv` rule, and re-accept the frozen evidence against the amendment.
* Or record a dated exception naming these four files, so the historical
  provenance record is not expected to cover test modules added after it.
* Or relocate the phase 2 tests under a separate directory and amend section 2
  and section 8 together.

## Reproduction

```bash
cd luminal-challenge
python3 verify_direct.py --stage all --output /tmp/verify_probe   # evidence: FAIL
PYTHONPATH=.reference:. python3 -m unittest tests_direct.test_evidence_checker
# -> FAILED (failures=2), both 'recorded_hashes:final'
```

The counterfactual, with the four modules temporarily moved aside and then
restored, is recorded above; `tests_direct.test_evidence_checker` then passes
64 of 64.
