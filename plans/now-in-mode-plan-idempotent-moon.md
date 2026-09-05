# AUDIT04 — the golden baseline

## Context

**The goal, in the author's words (2026-09-05): a clean scientific genesis — a
foundation solid enough that nothing built on it is built in fear.** Weeks are
an accepted cost. This plan is the route there, and it is deliberately *not* one
heroic push: the instrument is armed and useful at every commit along the way.

### What "golden" means here, operationally

"No more errors" is not reachable and this plan never claims it. Every defect in
every pass of this audit was found by a **detection method that did not exist
before that pass**; re-running existing gates has never once found something new.
So the destination is defined as a property of the *instrument*, not of the code:

1. every claim in a governance document has a gate;
2. every gate has been **observed to fail** by planting its defect;
3. the mutation kill rate is measured per owner, **no owner unmeasured**, every
   survivor adjudicated as coverage gap or equivalent mutant;
4. every module is covered to a declared floor, measured over a **complete**
   denominator;
5. every divergence between copies is **declared, reasoned and pinned** — zero
   undeclared exceptions;
6. expected values come from an **independent derivation**, never from what the
   code currently prints.

### Already landed (do not redo)

| phase | result | commit |
|---|---|---|
| **P0 mutation** | 28/28 scored. Semantic **23/25 = 92.0 %**, unit-test **19/25 = 76.0 %**. Zero-kill owners named; both survivors adjudicated; one prediction scored **failed** | `8b8c0e3` |
| **P1 coverage instrument** | 7 missing `__init__.py` added; report went 25 → 61 files; published 13 % was over less than half the code, true value **5.64 %**; denominator guard refuses on mismatch | earlier |
| **P2 import safety** | 61/61 modules import-safe by static scan; module-level RNG reseeds and directory creation removed | earlier |
| **P5 corpus diagnostic** | blocker is **917/5,204 = 17.6 %**, not 76.4 %; **1,943 of 3,977** nodes are derivable today | `601d939` |

### The three facts this plan is built on

```
49 of 61 files at exactly 0% coverage      5,365 statements unchecked
25 of 416 subproject files reach the core  6.0%
4 of 25 semantic mutants killed ONLY by a governance gate, no unit test
```

### Author decisions, 2026-09-05

- **Coverage: ratcheting floor.** Destination is 95 % on all 52 modules. The
  floor rises as each tier lands and **never falls**, so CI distinguishes a
  regression from unfinished work on every day of the build.
- **Core loading: guard new code, declare and pin existing divergences.** This is
  what the `monolithic-code` collapse protocol prescribes — non-zero elementwise
  disagreement means *two concepts*, not a collapse. `imp-pathinfo`'s mirror
  omits the in-degree field because it must reproduce someone else's published
  tables; that is **fidelity, not drift**, and collapsing it would make the
  replication unfaithful. Published numbers do not move.
- **`requests`: install and pin**, network mocked in tests.

---

## Phase A — close the holes the mutation run actually found

*Small, bounded, highest evidence-to-effort ratio. Nothing here is guesswork:
every target is a measured gap.*

| target | defect to catch | current |
|---|---|---|
| `NetworkIO` | `io-drop-logic`: loader reads the classification **label**, not the authoritative `logic` formula | **zero kills of any kind** |
| `deconvolution` | no semantic mutants exist at all — add them **first**, then the tests that kill them | **NOT MEASURED** |
| `CausalBoolCore` | `core-alloffsets`, `core-composed-y5`, `core-applygate-default` | 0/3 by unit test |
| `causalbool_paths` | `py-paths-root`: start path under `tests/`, which holds `results/` but not `src/` | killed by closure gate only |
| `BioMetrics` | `cformula-kofn`: nothing pins an **absolute** `C_formula` for KOFN | survivor |

`NetworkIO`, `CausalBoolCore` and `BioMetrics` are Wolfram owners, so their tests
are MUnit; `causalbool_paths` and `deconvolution` are pytest. Both suites are in
scope.

**Exit criterion:** re-run the harness; the **unit-test** kill rate must rise
from `19/25`, and no owner may remain `NOT MEASURED`. Report before and after.

## Phase B — coverage, tier by tier, floor ratcheting

**Tier 1 — 25 modules, 4,036 statements, on a published-number path**
(they write to `results/` or `figures/`). Largest: `DepMap_Validation` (916),
`Cancer_Corruption` (377), `bio_D_experiment` (322), `grn_data_pipeline` (247).

**Tier 2 — 24 modules, 1,329 statements**, everything else.

**The rule that makes the floor mean something:** every expected value is derived
from an **independent source** — a cost model written out in the test, a
published algorithm, a hand-computed case — and never from current output. A test
asserting current behaviour raises coverage and measures nothing. Not
hypothetical: the existing Lev4 LZ test asserts only `simple < periodic < random`,
which holds for **both** LZ76 and LZ78, so it passed while validating the wrong
measure. Pattern to follow: `tests/analysis/test_description_lengths_values.py`.

Where a module's correct output is a scientific judgement rather than a value
(scrapers, figure generation, orchestration), the test asserts **contracts** —
schema, invariants, refusal on bad input, determinism under a fixed seed. **Any
module receiving only contract tests is declared as such in `VERIFICATION.md`
with its reason**, so "covered" never silently means "executed".

Each tier lands in its own commit with its own measured floor.

## Phase C — the architecture guard

**Q1 owner:** none exists — `check_single_engine.sh` guards *named owners*, not
*consumers of owners*. **Q3:** this is a genuinely new concept (does each package
reach an owner?), so a new file is justified: `tools/check_core_loading.py`.

**Granularity is the whole design.** A package-level guard would pass **7 of 8**
packages and be near-vacuous — the comfortable-denominator failure this audit
keeps removing. The guard therefore works at **file** granularity: it finds files
implementing a core concept **by body fragment**, and requires each to import the
owner or appear in the exception ledger with a reason.

Every declared exception must carry an **elementwise measurement** of its
divergence from the owner, with the disagreement count printed — declaring a
divergence deliberate without measuring it is assertion, not evidence.

Prints the file count as its denominator; refuses on zero; verified by planting a
mirror.

## Phase D — prove the new tests bite

Extend the mutant catalogue to the newly covered modules, weighted to Tier 1.
**A module at 95 % coverage whose mutants all survive has tests that execute code
without checking it, and that must be visible.** Report the kill rate before and
after Phase B on the same catalogue, with survivors adjudicated and predictions
registered **before** the run.

## Phase E — genesis

`VERIFICATION.md`, `CORE.md`, `BASELINE.md` carry every moved number with its
cause. The floor is locked at its final value. `CLAUDE.md` gains the new
commands. **The result is tagged** — that tag is the genesis commit, and it is
the first state in this repository where every one of the six properties above
holds simultaneously.

---

## Critical files

- `.coveragerc` — `source` moves from the two owner import-names to `src/`;
  `fail_under` becomes the ratchet.
- `tools/check_coverage_ratchet.py` — **new owner**: global floor plus a per-file
  95 % floor for every module in a completed tier. `fail_under` is global only, so
  a global pass can hide a module at 0 %; that is exactly what this prevents.
- `tools/check_core_loading.py` — new, Phase C.
- `audit/AUDIT03_R2_collapse/mutation_harness.py` — extend the catalogue
  (enrich the owner; `--report` already exists there).
- `tests/analysis/`, `tests/MUnit/` — new tests; Wolfram gaps need MUnit.
- `requirements.txt` — pin `requests`.
- `GOVERNANCE/{VERIFICATION,CORE}.md`, `tests/MUnit/BASELINE.md`, `CLAUDE.md`.

## Verification

```bash
# Phase A — did the holes close?
venv/bin/python audit/AUDIT03_R2_collapse/mutation_harness.py --all --resume
venv/bin/python audit/AUDIT03_R2_collapse/mutation_harness.py --report
#   unit-test kill rate must exceed 19/25; no owner may read NOT MEASURED

# Phase B — per tier
venv/bin/python -m pytest -q tests/ --cov=src --cov-report=term
venv/bin/python tools/check_coverage_ratchet.py     # global + per-file floors
#   plant: drop one test from a completed tier -> must go red

# Phase C
venv/bin/python tools/check_core_loading.py         # prints its file denominator
#   plant: add a mirror of a core concept -> must go red

# standing bars, unmoved
zsh tools/run_closure.sh pure                       # 9/9
make ci-local                                       # closure-wolfram + MUnit
venv/bin/ruff check --output-format=concise .       # enforced set clean
make test-subprojects                               # 28 / 97 / 47 / 41
```

**Rules that hold throughout.** Every gate refuses on empty input and prints its
denominator. Every new gate is verified by planting its defect **in the same
commit**. No number enters a document without its reference distribution in the
same sentence, and none is typed by hand where a tool can produce it. Expected
values come from an independent derivation. Archives under `doc/` and
`workspaces/` are not rewritten. **No Claude co-authorship in any commit.**

**Acceptance.** All 52 modules at the 95 % floor over a complete 61-file
denominator, or every shortfall declared with its reason; mutation kill rate
reported per owner with **no owner unmeasured**; every subproject file
implementing a core concept either imports the owner or is a declared, measured,
pinned exception; every governance claim gated by a tool observed to fail.

**Stop conditions.** No attempt to unblock R4/R5 — diagnosis only, the author
gate stands. No regeneration of bio numbers. No producer wiring for the 29
uncovered manuscript tables. No rewriting of `doc/` or `workspaces/` archives. No
style lint beyond the enforced `F` set. **No collapse of a divergence that has
not first been measured elementwise.**
