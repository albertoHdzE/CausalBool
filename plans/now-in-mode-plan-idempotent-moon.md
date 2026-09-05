# AUDIT03-C — make the gates run without me, and measure whether they bite

## Context

Four audit passes built a defensible **structure**: one owner per concept
(`GOVERNANCE/CORE.md`), guards that fire, declared test membership
(`tests/MUnit/MANIFEST.tsv`), `OK=69 FAIL=0 TOTAL=69`, closure at 9 members.

The **process** around it does not exist. Measured on 2026-09-04:

- **No CI.** There is no `.github/` directory at all. Every gate runs only when
  I remember to run it. A guard nobody runs is a comment.
- **`make closure` cannot be a CI gate as written.** Every member is invoked
  with a `-@` prefix, which tells make to ignore the error, so **the target
  exits 0 even if all nine members fail**. The rationale for that prefix — "a
  non-zero exit is expected while an owned red remains in the MUnit ledger" — is
  obsolete: the ledger is `FAIL=0`.
- **No dependency manifest at root.** Only the four subprojects have one, so CI
  cannot install reproducibly. Local interpreter is Python 3.13.12, 76 packages.
- **No linter or type config anywhere** — no `ruff.toml`, `setup.cfg`,
  `mypy.ini`, `pyproject.toml`, `.pre-commit-config.yaml`.
- **Two gates sit outside closure**: `tools/run_crosscheck_parity.sh` (the
  135/135) and `tools/test_description_length_parity.py`.
- **Test quality is unmeasured.** One hand-run mutant (`MAJORITY` tie threshold,
  `Floor[d/2]+1` → `Ceiling[d/2]`) was caught by **5 tests across 4 sections**.
  That is a spot check, not a kill rate.

### The residue that must be cleared first

The working tree carries **77 modified files**, and they are not all noise:

- **52 of 77** differ only in timing, memory or dates — covered by the existing
  volatility exclusion (`BASELINE.md` AC-0.2a), whose standing rule is *revert
  rather than commit noise*.
- **The remaining 25 are the mutation experiment's output.** Five status files
  read `FAIL` (`algo004closedformsetaudit`, `analysis_analyticvsexhaustive`,
  `analysis_majority`, `gates013onesetallfamilies`, `mixed001FormulaVsExhaustive`)
  and `results/tests/runall/Status.txt` reads `OK=64 FAIL=5 TOTAL=69`.

**My mutation run restored `Gates.m` but not the artefacts.** That is exactly the
stale-artefact class this audit spent a pass fixing, reintroduced by the tool
built to test for it. Committing this would record a false red baseline.

**Design consequence, and the reason it leads the plan:** the mutation harness
must run in an **isolated git worktree**, never in the working tree. A worktree
shares the 11 GB object store, so it is cheap.

### Decisions taken 2026-09-04

- **Wolfram tier stays local.** CI covers the pure tier; the Wolfram tier gets a
  `make ci-local` target and a **pre-push hook** so it cannot be silently
  skipped.
- **Mutation harness: ~40 mutants, broad sweep**, run overnight.
- **Scope: CI + mutation + lint + the two orphaned gates**, plus the tree. The
  29 uncovered manuscript tables are explicitly **out**.

---

## The pass, in execution order

### 1. Clear the mutation residue — before anything else

Re-run the full suite to regenerate artefacts from unmutated sources. Assert
`OK=69 FAIL=0 TOTAL=69` and that **no status file reads `FAIL`**. Then apply the
standing policy: revert files whose only diff is timing/memory/date, and inspect
any residual non-volatile diff individually before it is committed.

Do not proceed to any other item until the tree is clean and the rollup is green.

### 2. `make closure` must be able to fail

Replace the error-swallowing recipe with one that runs every member, prints
every verdict, and **exits non-zero if any member failed**. Each member must
still report independently — the point of the `-` prefix was that one red should
not hide the other eight, and that property is kept by collecting statuses and
failing at the end.

Split the target so CI can address the tiers separately:

- `make closure-pure` — the 7 members needing no Wolfram
- `make closure-wolfram` — `check_wolfram_syntax.wl`, `verify_paper_artefacts.py`
  (it shells out to `producer_cmd`), plus the two orphaned gates
- `make closure` — both, unchanged in meaning for local use
- `make ci-local` — `closure-wolfram` + the MUnit suite

**Verify by planting a failure** in one member and confirming each target's exit
code moves. A gate aggregator that cannot go red is the defect being fixed.

`tools/check_glossary_sync.sh` exits **2 (SYNC-UNKNOWN)** when the sibling repo
is absent, which is correct refusal behaviour and is what CI will see. CI must
report SYNC-UNKNOWN **as unknown**, never fold it into a pass.

### 3. Root dependency manifest

Add a pinned `requirements.txt` (runtime) and `requirements-dev.txt` (pytest,
ruff) generated from the working venv, with `pybdm==0.1.0` honoured as the
already-declared pin in `src/description_lengths.py`. Confirm a clean
`python -m venv` + install reproduces the root pytest result (**32**) and
index-deconvolution (**146**).

### 4. CI — the pure tier

`.github/workflows/ci.yml`, Python 3.13, triggered on push and pull request:

| job | contents |
|---|---|
| `gates` | `make closure-pure`; glossary sync reported as SYNC-UNKNOWN with its reason |
| `tests` | root `tests/analysis` (32) and `index-deconvolution` (146) |
| `subprojects` | matrix over the four replication packages, each with its own manifest — expected **28 / 97 / 47 / 41** |
| `lint` | `ruff check` (see item 6) |

Every job asserts an expected count, so a suite that collects **zero** tests
fails instead of passing silently — the same law the gates already follow.

CI must **not** run the Wolfram tier and must **say so in its summary**, so a
green badge cannot be mistaken for full coverage.

### 5. The Wolfram tier cannot be silently skipped

`tools/install_hooks.sh` sets `core.hooksPath` to a tracked `githooks/`
directory (`.git/hooks` is not version-controlled) and installs a **pre-push**
hook running `make ci-local`. The hook must be bypassable with an explicit
`--no-verify` and must print what it skipped when bypassed.

Fold `run_crosscheck_parity.sh` and `test_description_length_parity.py` into
`closure-wolfram`. Both exist and neither has ever been run by a routine command.

### 6. Lint — correctness rules first, style deferred

370 Python files have never been linted, so a full ruleset would produce an
unusable wall of style findings. Enable the **pyflakes (`F`) family only** to
begin with: undefined names, unused imports, f-strings without placeholders,
redefinitions. These are the rules that catch *bugs* — `F821` is the class that
would have caught the dead `a, b = params["pair"]` unpack by machine rather than
by my reading it.

**Report the finding count with its denominator before fixing anything.** Fix
genuine defects; for anything intentional, add a scoped `noqa` with a reason,
never a blanket ignore. Style rules (`E`/`W`) are enabled only after `F` is
clean, and are out of scope for this pass.

### 7. The mutation harness — the measurement that matters

`audit/AUDIT03_R2_collapse/mutation_harness.py`. Not a rewrite: it reuses the
existing suite runners and the isolation lesson from item 1.

**Design constraints, each from a defect already seen in this programme:**

- **Runs in a `git worktree`**, so a mutant cannot leave residue in the working
  tree. Cleaned up on exit including on interrupt.
- **The mutant catalogue is declared in the file**, one to several per owner in
  `GOVERNANCE/CORE.md` — gate semantics, index algebra, description length,
  `C_formula`, corpus loader, offsets, deconvolution, paths — plus boundary and
  off-by-one cases. Target ≈40.
- **Each mutant is verified to apply.** A mutation that silently fails to patch
  its target would be scored as "killed by nothing" and inflate the rate; the
  harness refuses on a no-op patch.
- **Each mutant is routed to the full tier that could catch it** — MUnit for
  Wolfram owners, the whole pytest set for Python owners. Not a hand-picked
  subset, which would bias the result toward a kill.
- **Prints the denominator**: `killed/total`, per owner, and never a bare
  percentage.

**Survivors are adjudicated, not counted.** A surviving mutant is either a
**coverage gap** or an **equivalent mutant** that changes nothing observable —
these are not the same finding and conflating them is the classic mutation-score
error. Every survivor is inspected and labelled in `MUTATION.md`, with the
owners that have **zero** kills named explicitly, since those are the real
result.

Expected cost ≈3.5 h (Wolfram mutants dominate at ~8 min each); run in the
background.

### 8. Ledger

`tests/MUnit/BASELINE.md` gains the kill rate and the CI split. `CORE.md` gains
the CI/hook entries in its guard table and `check_core_index.sh` must stay green.
`DUPLICATION.md` records the mutation-residue incident, since it is a fresh
instance of the stale-artefact class and was caused by my own tool.

---

## Critical files

- `Makefile` — the `-@` recipe prefixes; new `closure-pure` / `closure-wolfram` /
  `ci-local` targets.
- `.github/workflows/ci.yml`, `requirements.txt`, `requirements-dev.txt`,
  `ruff.toml` — all new.
- `githooks/pre-push`, `tools/install_hooks.sh` — new; `core.hooksPath`.
- `audit/AUDIT03_R2_collapse/mutation_harness.py`, `MUTATION.md` — new.
- `tools/check_glossary_sync.sh` — unchanged; its exit 2 is *correct* and CI must
  honour it.
- `tests/MUnit/BASELINE.md`, `GOVERNANCE/CORE.md`,
  `audit/AUDIT03_R2_collapse/DUPLICATION.md` — the ledger.

Reuse, do not reimplement: `tests/MUnit/run-tests.sh` (suite), the nine closure
members, `orphan_census.py` / `duplication_census.py` / `test_efficacy_census.py`
(census shape and the refuse-on-empty pattern).

## Verification

```bash
# 1. tree — the gating step
zsh tests/MUnit/run-tests.sh --all            # OK=69 FAIL=0 TOTAL=69
grep -rl . results/tests/*/Status.txt | xargs -n1 head -1 | sort -u   # no FAIL
git status --short | wc -l                    # only volatile files remain, then reverted

# 2. closure must be able to fail — verified by planting, not asserted
make closure-pure   ; echo $?                 # 0
make closure        ; echo $?                 # 0
#   plant a failure in one member -> each affected target must exit non-zero

# 3-4. reproducible install, then the pure tier exactly as CI runs it
python3 -m venv /tmp/ci-probe && /tmp/ci-probe/bin/pip install -r requirements.txt -r requirements-dev.txt
/tmp/ci-probe/bin/python -m pytest -q tests/analysis          # 32
(cd index-deconvolution && /tmp/ci-probe/bin/python -m pytest -q)   # 146

# 5. the hook must actually fire
zsh tools/install_hooks.sh && git config core.hooksPath       # githooks
#   a push with a failing Wolfram tier must be refused

# 6. lint — count first, fix second
venv/bin/ruff check --select F --output-format=concise . | wc -l

# 7. mutation — isolated, with its denominator
venv/bin/python audit/AUDIT03_R2_collapse/mutation_harness.py --all
git worktree list                             # must be back to one entry
git status --short | wc -l                    # must be 0 — no residue

# standing bars, unmoved
make ci-local                                 # closure-wolfram + MUnit
for d in imp-causal-paper imp-prices imp-causalNet-paper imp-pathinfo-paper; do
  (cd $d && .venv/bin/python -m pytest -q -p no:warnings); done   # 28 / 97 / 47 / 41
```

**Rules that hold throughout** (carried forward):

- **Every gate refuses on empty input and prints its denominator.** A suite that
  collects zero tests fails; `SYNC-UNKNOWN` is reported as unknown, never as a
  pass.
- **Every new gate is verified by planting the defect** and observing it fail, in
  the same commit.
- **No number enters a document without its reference distribution in the same
  sentence** — the kill rate carries its denominator and its survivor
  adjudication.
- **Revert noise rather than commit it**; declare every intended delta in
  `BASELINE.md` with its cause.
- **No Claude co-authorship in any commit.**

**Acceptance.** Tree clean and green with the mutation residue gone; `make
closure` demonstrably able to fail; a reproducible install; CI running the pure
tier on every push and stating plainly that the Wolfram tier is not covered; the
pre-push hook refusing a push whose Wolfram tier is red; `ruff --select F` clean
or every remaining finding justified in place; a kill rate reported per owner
with survivors adjudicated as gap-or-equivalent and zero-kill owners named.

**Stop conditions.** No producer wiring for the 29 uncovered manuscript tables.
No style-rule lint beyond `F`. Bio regeneration does not start (blocked behind
R4). R4.2–R4.5 do not start. R5 does not start (`Q2.2` unresolved).
