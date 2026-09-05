# Verification status — what is checked, how, and how well

**Status:** normative. **Last measured:** 2026-09-04 (AUDIT03-C).
**Regenerate every number here with `make ci-local`; none of them is typed by hand.**

This is the single page a reviewer needs. `CORE.md` says who owns what;
`BASELINE.md` is the test ledger; this says **what is actually verified, and to
what degree** — including the parts that are not.

---

## 1. How to run it

```bash
make closure-pure     # 7 gates, no Wolfram needed — this is what CI runs
make closure-wolfram  # 4 gates that need a licensed local kernel
make closure          # both
make suite            # the 69-test MUnit suite
make ci-local         # closure-wolfram + suite: everything CI CANNOT run
make lint             # ruff, enforced rule set
make hooks            # install the pre-push hook (once per clone)
```

**`make ci-local` before every push.** The pre-push hook runs it for you and
refuses a push whose Wolfram tier is red; bypass with `git push --no-verify`,
which prints exactly what went unchecked.

---

## 2. The two tiers, and why the split is not cosmetic

GitHub-hosted runners have **no licensed WolframKernel**. Roughly half this
programme's verification therefore cannot run in CI, and pretending otherwise
would be worse than not having CI at all.

| tier | members | runs in CI |
|---|---|---|
| **pure** | paper-number gate · GLOSSARY sync · GLOSSARY conformance · single-engine guard · core index · test manifest · table coverage · **verification numbers** | **yes** |
| **wolfram** | `.m`/`.wl` syntax (153 files) · paper artefacts (executes producers) · cross-language parity (135/135) · description-length parity | **no** |
| **suite** | 69 MUnit tests | **no** |

CI states this in its own header and emits a run warning. **A green badge means
the pure tier passed — nothing more.**

> **The aggregator used to be unable to fail.** `make closure` invoked each
> member with a `-@` prefix, which tells make to ignore the error, so it exited
> `0` even if all nine failed; one member piped into `head`, so its status was
> `head`'s. `tools/run_closure.sh` replaced it and is verified in all three
> states — planted failure → exit 1, absent sibling → `UNKNOWN` reported as
> unknown, clean → 0.

**Three states, not two.** `check_glossary_sync.sh` exits `2` when the sibling
repository is absent. That is correct refusal, and it is what CI sees.
`UNKNOWN` is never folded into a pass.

---

## 3. Measured status

| what | measured | gate |
|---|---|---|
| MUnit suite | **69 / 69**, 0 failures | `make suite` |
| `tests/analysis` | **134** tests | CI asserts the count |
| Owner line+branch coverage | **98.56 %** | fails below **95 %** |
| `index-deconvolution` | **146** tests | CI asserts the count |
| Replication packages | **28 / 97 / 47 / 41** | CI matrix, each count asserted |
| Wolfram files that parse | **153 / 153** | `check_wolfram_syntax.wl` |
| Test files classified | **82 / 82** (69 test, 13 producer, 0 quarantine) | `check_test_manifest.sh` |
| Owners named in `CORE.md` that exist | **41 / 41** | `check_core_index.sh` |
| Manuscript numbers unchanged | **138** entries identical | `snapshot_paper_numbers.py` |
| Lint, enforced rules | **clean** | `ruff check` |

### Coverage of the declared Python owners

| owner | coverage |
|---|---|
| `src/description_lengths.py` | **100 %** |
| `src/causalbool_paths.py` | **96 %** |

Scoped to the owners on purpose. A percentage averaged over 370 files — scrapers,
one-off analyses, frozen workspaces — moves for reasons nobody cares about and
hides the one that matters.

> **Coverage is a floor, not a goal.** 100 % of lines executed says nothing
> about whether the assertions are any good. The mutation harness is what
> measures that.

### This table now checks itself — for 5 of its 9 numbers

The header above claims none of these figures is typed by hand. **That sentence
was false when it was written:** the `check_core_index.sh` row read `36 / 36`
while the guard itself printed `40 / 40`. Nothing compared the page to the tools
it cites, so a governance document about verification was the least verified
artefact in the repository.

`tools/check_verification_numbers.py` (pure tier) parses this section and
re-derives each claim from the tool named beside it. Of the **9 numeric rows in
the table above** it checks **5** and **names the 4 it does not** — MUnit,
coverage, the Wolfram parse and the manuscript snapshot are wolfram-tier or
expensive, so they are declared unchecked rather than quietly skipped. Verified
in all three states: a planted `36 / 36` exits `1`, an unparseable table exits
`2`, clean exits `0`.

It has already earned its place twice. It rejected the stale `36 / 36`, and when
this gate was itself added to `CORE.md` the owner count moved to `41` and the
page went red until it was corrected — which is precisely the drift that had
been invisible.

Absent subproject virtualenvs report **UNKNOWN**, never a pass — the same
three-state discipline as the glossary sync.

---

## 4. Where verification is thin — stated, not buried

| gap | measured | why it is open |
|---|---|---|
| **Manuscript tables with a producer wired** | **5 of 34 (15 %)** | The gate's old summary read *"7 covered, 1 pending"*, which invites 88 %. The pending entry was an unenumerated catch-all. Wiring the remaining 29 is research-shaped: some have no producer at all. |
| **Lint hygiene debt** | F401 **176** · F541 **47** · F841 **47** | Declared in `ruff.toml`, not hidden. Turning 270 findings red would block every push. Several need adjudication rather than deletion. |
| **`Trajectory_LZ.py` `k_max`** | initialised, never used | The function cites Kaspar & Schuster (1987), whose formulation *does* use it. This is a valid simplified variant, but deleting the variable would erase the signal that it diverges from its own citation. **A scientific question, not a lint one.** |
| **Mutation kill rate** | in progress | See §5. |
| **Bio regeneration, R4.2–R4.5, R5** | blocked | 3,977 of 5,204 corpus nodes have no derivable Boolean truth table; `Q2.2` is an unresolved measurement conflict. |

---

## 5. Does green mean anything? The mutation measure

A test count is not a measure of test quality. This programme has already found
a parity harness printing `cases matched: 0/0 / all match: True`, a verifier
reading a key one level too deep, eleven files exporting a literal `"OK"`, and
three files reported green while syntactically broken.

`audit/AUDIT03_R2_collapse/mutation_harness.py` plants **28 declared mutants**
across the owners in `CORE.md` — inverted comparisons, off-by-ones, dropped
branches, swapped constants — and reports how many the verification set kills.

Design constraints, each earned from a defect already seen here:

- **Runs in a git worktree.** The hand-run mutation restored `Gates.m` but not
  the artefacts, leaving five `FAIL` status files in the working tree — the
  stale-artefact class this audit removed, reintroduced by the tool built to
  test for it.
- **No routing.** Every mutant faces the whole suite, both pytest sets and both
  closure tiers. The first version routed by owner language and produced a
  *false* coverage gap.
- **Segfaults are not kills.** `run-tests.sh` prints `FAIL: X -> PASS (kernel
  exit=139)` under memory pressure — the test passed, the kernel died. Counting
  it would inflate the one number this exists to get right.
- **The baseline must be green, or it refuses.** It did refuse, and that refusal
  found a real defect: see below.
- **Survivors are adjudicated, never scored.** A survivor is a **coverage gap**
  or an **equivalent mutant**; conflating them is the classic error.

**Known result so far:** one hand-run mutant (`MAJORITY` tie threshold, breaking
declared convention D-3) was killed by **5 tests across 4 sections**. The full
rate lands in `mutation_results.json` and `BASELINE.md`.

### What the harness found before it ran a single mutant

`TSK-NATURE-LEV3-SETUP-002` **passed in the working tree and failed in a clean
worktree**. Root cause, measured:

```
repo root      python3 -> ~/.pyenv/versions/3.13.12/bin/python3   (has numpy)
/tmp/worktree  python3 -> ~/.pyenv/versions/3.11.10/bin/python3   (does not)
```

`BioBridge_v2.m` shelled out to a bare `python3`, and pyenv resolves the shim
per directory — so the same test gave a different verdict depending on where it
ran. The interpreter is now declared. **A test that is not hermetic is not a
test of this repository.**

---

## 6. Related

`CORE.md` (owners and guards) · `BASELINE.md` (the test ledger and every
declared delta) · `DESCRIPTION_LENGTHS.md` (variants A–E) · `GLOSSARY.md`
(definitions) · `LARGE_BINARIES.md` · `audit/AUDIT03_R2_collapse/DUPLICATION.md`
and `ORPHANS.md` (the censuses).
