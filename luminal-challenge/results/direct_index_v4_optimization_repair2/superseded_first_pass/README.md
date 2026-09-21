# Superseded first pass of the F1/F2 repair round

Retained, not deleted. These three artifacts were measured and recorded before
the regression fixture was finished, and they are superseded by the trees one
level up.

## What happened

The `evidence` verification stage runs the checker's own regressions, and those
regressions need a verification artifact to audit. The fixture built one, and
for the isolated-corpus acceptance step it read the 142 corpus inputs out of
`verification/corpus` — a directory that the *acceptance* stage materialises,
and acceptance runs **after** evidence. On the first pass of a fresh tree that
directory did not exist yet, so the fixture produced an empty corpus and six
tests failed:

```
evidence/evidence: FAIL tests=64
    4 errors  IndexError on an empty evidence["runs"]
    2 failures  control: ['present:corpus_manifest.json', 'verification_corpus']
```

That is the fixture depending on the run that contains it — the same class of
self-reference the previous round hit with `summary.json`. The fix was to give
the fixture its own inputs: it now materialises the corpus itself through
`verify_direct.materialise_corpus`, the function that owns writing it, so the
record, the evidence file and the inputs are one consistent set however far
along the surrounding verification happens to be.

**No check was weakened to make this pass.** The corpus totals are still counted
from 142 real generated programs and must still be 142 programs and 277 cases.

## Why these artifacts were remeasured rather than kept

Fixing the fixture changed `tests_direct/test_evidence_checker.py`, and both the
benchmark report and the verification summary record the SHA-256 of every test
file. The recorded hashes no longer matched the working tree, so the whole chain
was rerun after the scripts were final, as the lead's handoff requires.

## What is here

| Artifact | Status | Note |
|---|---|---|
| `final/` | complete, exit 0 | every mandatory gate PASS; superseded on hashes alone |
| `comparison/` | complete, exit 0 | all seven gates PASS; superseded on hashes alone |
| `verification/` | **exit 1** | the `evidence` stage failure described above |

The `final/` and `comparison/` numbers are sound measurements taken from the
same sources; they are superseded because their provenance no longer points at
the final scripts, not because anything in them was wrong.
