# AUDIT04 — a testing instrument that can fail, then 95% of `src/`

## Context

AUDIT03-C delivered CI, a closure gate that can go red, a pre-push hook, a lint
ratchet, and 134 unit tests at a 95% floor on the declared owners. Executing it
also found **six defects**, none of them by re-running an existing gate — every
one came from a detection method that did not exist before:

| defect | how it was found | status |
|---|---|---|
| MH sampler called itself adaptive above a fixed `prop_sd = [0.5, 0.5]` | triaging F841 instead of deleting it | fixed; acceptance 0.19 → 0.39–0.47, ESS σ +36%, μ unchanged |
| `c29` Bernoulli null nested inside its own comparator in **100%** of draws | same | fixed; nesting → 0%, *r* +0.724 → −0.025 |
| **61%** of GINML files silently binarised, 304 nodes losing level rules | same | fixed; recorded and warned |
| `datasaurus` G4 asserted a Monte Carlo *z* to ±0.01 with SE ≈0.16 | re-running after a fix | fixed; asserts separation, not a sample value |
| a measure labelled LZ76 that computes **LZ78** (2% agreement with its own label) | measuring two implementations rather than reading them | fixed; two names + forwarder |
| a 4-hour measurement with no crash resilience | a reboot destroyed 10/28 mutants | fixed; per-mutant persistence |

**The remaining problem is not defects — it is that the instrument cannot see.**
Measured 2026-09-05:

```
coverage of the declared owners        98.56%   ← 99 statements, 2 files
coverage reported for src/                13%   ← over 25 of 54 files
files coverage never reports              29    ← ~4,574 non-blank lines
src/ modules imported by no test          26 of 53
```

**Root cause, established by correlation and exact:** coverage can only enumerate
*unexecuted* files inside importable packages. `src/data` and `src/integration`
have `__init__.py` and are fully reported (4/4, 18/18). The seven directories
without one — `analysis`, `complexity`, `dynamics`, `experiments`, `pipeline`,
`scripts`, `stats` — contribute only the files a test happened to import.

So **the published 13% is itself over a partial denominator**, and the true
figure is roughly half that. A 95% floor on `src/` imposed today would be
measured over whatever the tests already touch and **could never fail** — the
same class as the `-@` Makefile prefixes this programme already removed.

**Author decisions taken 2026-09-05:** cover **all 53 `src/` modules to a 95%
floor**; treat the R4/R5 corpus blocker with a **diagnostic phase** (measure why,
do not attempt to unblock).

### What "clean" means here, operationally

"No more errors" is not reachable and this plan does not claim it. What is
reachable and auditable:

1. every claim in a governance document has a gate;
2. every gate has been **observed to fail** by planting its defect;
3. the kill rate is measured, with every survivor adjudicated as coverage gap or
   equivalent mutant;
4. every module that produces a published number is covered to the declared
   floor, and the floor is measured over a **complete** denominator;
5. zero undeclared exceptions.

---

## Phases, in execution order

### Phase 0 — land the mutation result *(blocking input; ~3h, already running)*

Finish AUDIT03-C item 7 against `c9bc412`. Nothing in Phase 3 may start before
this, because the harness records **which tests caught each mutant**
(`killed_by`), and that is the only evidence-based way to choose test targets.
Choosing them any other way is guessing, which is the error this whole audit has
been removing.

- Kill rate per owner **with its denominator**; owners with **zero** kills named.
- Every survivor adjudicated against the predictions registered **in advance** in
  commit `8888376` — including `py-paths-root`, predicted to survive as a real
  coverage gap in tests I wrote, with its failing input named (`tests/` holds
  `results/` but not `src/`).
- The three **reachability probes** reported separately and excluded from the
  headline rate.
- Write `audit/AUDIT03_R2_collapse/MUTATION.md` results section; update
  `BASELINE.md` and `VERIFICATION.md` §5.

### Phase 1 — make the instrument able to fail *(before any test is written)*

1. Add `__init__.py` to the seven non-package directories under `src/`. Verify no
   import breaks: the suites resolve modules via `sys.path.insert(0, ROOT/"src")`
   and import as `complexity.Trajectory_LZ`, which a real package still satisfies.
2. Re-measure. Expect the report to jump from 25 to **54 files** and the
   percentage to **fall**. Record the corrected baseline.
3. **Correct `VERIFICATION.md`**: the committed `13%` is over 25 of 54 files and
   must be restated with its true denominator.
4. **A denominator guard.** `tools/check_verification_numbers.py` gains a check
   that the number of files in the coverage report equals the number of `.py`
   files on disk under `src/`, and **refuses** when they differ. Without it, a
   future directory added without `__init__.py` silently leaves the measurement
   again. Verified by planting: remove one `__init__.py`, watch it go red.

### Phase 2 — importability, measured not assumed

Seven of the 29 invisible modules have no `__main__` guard. Having a guard is not
the same as being side-effect-free on import: check each by importing it in a
subprocess and asserting it neither runs work nor writes to `results/`.
Files that do are refactored so the top-level body moves into a function behind
a guard. This is a prerequisite for testing them at all.

### Phase 3 — tests, in evidence order

**Priority is set by consequence, not by file size.** 16 of the 29 invisible
modules write to `results/` or `figures/` — they are on a published-number path.
They come first; the rest follow.

**The rule that makes the 95% floor mean something:** every expected value must be
derived from an **independent source** — a cost model written in the test, a
published algorithm, a hand-computed case — and never from what the code
currently prints. A test that asserts current behaviour raises coverage and
measures nothing. This is not hypothetical: the existing Lev4 LZ test asserts
only `simple < periodic < random`, which holds for **both** LZ76 and LZ78, so it
passed while validating the wrong measure.

Reuse the pattern already established in `tests/analysis/test_description_lengths_values.py`:
the expected cost model is written out in the test file, independently of
`src/description_lengths.py`, then compared.

Where a module's correct output is a scientific judgement rather than an
assertion (scrapers, figure generation), the test asserts **contracts** —
schema, invariants, refusal on bad input, determinism under a fixed seed — not
values. Any module where even that is not meaningful is **declared** in
`VERIFICATION.md` with its reason rather than given a vacuous test.

### Phase 4 — prove the new tests bite

Extend the mutant catalogue in `audit/AUDIT03_R2_collapse/mutation_harness.py`
to the newly covered modules, weighted toward the 16 on a published-number path.
A module at 95% coverage whose mutants all survive has tests that execute code
without checking it, and that must be visible.

Report the kill rate before and after Phase 3 on the same catalogue.

### Phase 5 — R4/R5 diagnostic *(measurement only, no fix attempted)*

`3,977 of 5,204` corpus nodes (76.4%) carry a label outside the twelve families,
their formulas being multi-valued threshold expressions recorded unevaluable at
AUDIT02/H. Characterise, do not repair:

- breakdown by **source format** (SBML / GINML / BNet / Cell Collective) and by
  declared gate label;
- how many are the **GINML multi-valued** nodes this audit just surfaced
  (582 nodes, 108 files, 304 losing level rules) — i.e. how much of the blocker
  is the binarisation defect rather than a genuinely new gate family;
- how many fall under the proposed thirteenth family `REGULATORY_DNF`
  (2,079 of 2,486 of the `CUSTOM` set).

Output: `audit/AUDIT04_corpus_diagnostic/FINDING.md` with counts and their
denominators. **No description length is recomputed and no bio number is
regenerated** — the author gate on R4 stands.

### Phase 6 — ledger and ratchet

`VERIFICATION.md`, `CORE.md`, `BASELINE.md` updated with every moved number and
its cause. The coverage floor becomes a ratchet on the **complete** denominator.
`CLAUDE.md` gains the new commands.

---

## Critical files

- `.coveragerc`, `pytest.ini` — scope and floor; the floor moves only after
  Phase 1 makes the denominator complete.
- `src/{analysis,complexity,dynamics,experiments,pipeline,scripts,stats}/__init__.py`
  — new, seven files, the whole reason the instrument is blind.
- `tools/check_verification_numbers.py` — enrich with the denominator guard
  (**do not** write a second gate; this is the owner of "the document matches its
  tools").
- `audit/AUDIT03_R2_collapse/mutation_harness.py` — extend the catalogue.
- `tests/analysis/` — new tests follow `test_description_lengths_values.py`.
- `GOVERNANCE/VERIFICATION.md`, `GOVERNANCE/CORE.md`, `tests/MUnit/BASELINE.md`.

## Verification

```bash
# Phase 1 — the instrument, before anything is written
venv/bin/python -m pytest -q tests/analysis --cov=src --cov-report=term
#   files reported must be 54, not 25; the percentage must FALL
zsh tools/run_closure.sh pure                 # denominator guard included
#   plant: delete one __init__.py -> the guard must go red

# Phase 3/4 — do the tests bite?
venv/bin/python audit/AUDIT03_R2_collapse/mutation_harness.py --all --resume
#   kill rate per owner, with denominators; zero-kill owners named

# standing bars, unmoved
make ci-local                                  # closure-wolfram + 69 MUnit
venv/bin/ruff check --output-format=concise .  # enforced set clean
make test-subprojects                          # 28 / 97 / 47 / 41
```

**Rules that hold throughout** (carried forward):

- Every gate **refuses on empty input** and **prints its denominator**.
- Every new gate is verified by **planting the defect** in the same commit.
- No number enters a document without its reference distribution in the same
  sentence; no number is typed by hand where a tool can produce it.
- Expected values come from an independent derivation, never from current output.
- Archives under `doc/` and `workspaces/` are **not** rewritten.
- No Claude co-authorship in any commit.

**Acceptance.** Coverage measured over **54 of 54** files with a guard that
refuses a partial denominator; 95% floor met on that complete denominator or
every shortfall declared with its reason; a kill rate reported per owner before
and after the new tests, with survivors adjudicated; the corpus blocker
characterised with counts and denominators.

**Stop conditions.** No attempt to unblock R4/R5 — diagnosis only. No
regeneration of bio numbers. No producer wiring for the 29 uncovered manuscript
tables. No rewriting of `doc/` or `workspaces/` archives. No style lint beyond
the enforced `F` set.
