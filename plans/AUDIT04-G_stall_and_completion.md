# AUDIT04-G — the intermittent stall, the SIGSEGV, and the completion of AUDIT04

**Status:** open
**Branch:** `fixing`
**Written:** 2026-09-08
**Anchor commit:** `20b2ae1` (pushed; `origin/fixing` is identical, verified by `git rev-parse`)
**Author:** Alberto Hernández Espinosa
**Preceding plan:** `plans/now-in-mode-plan-idempotent-moon.md` (AUDIT04-F, completed)
**Master plan:** `AUDIT_FIXING_PLAN_01.md` (waves; still the governing document for Parts A–G)

---

## 0. How to read this document

This plan is written for an agent starting with **no memory of the preceding
sessions**. Everything needed to act is stated here or named by path. Where a
number appears, its **producer** is named, because a number without a producer
drifts — that failure has already happened twice in this repository and is
recorded in `GOVERNANCE/VERIFICATION.md`.

Three habits are mandatory and are not stylistic:

1. **Measure, do not assert.** Every claim of the form "X is clean / X agrees /
   X is fixed" must name the command that produced it and the denominator it
   ran over. `all match: True` over zero cases is the failure this project
   exists to stop.
2. **Report the reference distribution in the same sentence as the number.**
   "The gap is 27 bits" is not a result. "The gap is −27.68 bits, and the
   network beats every one of its 1000 nulls in 53 of 231 cases" is.
3. **Falsify your own hypothesis before you commit it.** Section 3.1 below
   records two hypotheses of mine that were wrong, and the measurement that
   killed each. That record is the most useful part of this document.

---

## 1. What this project is

CausalBool is a deterministic, physics-inspired programme of **algorithmic**
information theory for Boolean causal networks. It derives closed-form
index-set formulae that reconstruct synchronous network outputs exactly,
without probabilistic assumptions.

**It is algorithmic (Kolmogorov / AID), never Shannon.** This is not a
preference; it is the identity of the programme. See §2.4.

- **Wolfram core:** `src/Packages/Integration/` — gate semantics, index-set
  algebra, repertoire dynamics. This is the formalised API surface.
- **Python layers:** `src/analysis/`, `src/complexity/`, `src/stats/`,
  `src/integration/` — data ingestion, analysis pipelines, validation.
- **Governance:** `GOVERNANCE/` — `CORE.md` (one owner per concept),
  `VERIFICATION.md` (what is checked, to what measured degree, and what is
  **not**), `GLOSSARY.md` (definitions, synced from a sibling repository).
- **Papers:** `papers/method/manuscript_formal/` (Paper B, solo, proofs) and
  `papers/method/manuscript_computational/` (Paper A, with Hector Zenil).

Read in this order before touching anything: `CLAUDE.md` →
`GOVERNANCE/CORE.md` → `GOVERNANCE/VERIFICATION.md` → `GOVERNANCE/GLOSSARY.md`.

---

## 2. Confirmed state at `20b2ae1`

All figures below were produced by the named command on 2026-09-08.

### 2.1 Gates, all green

| gate | command | result |
|---|---|---|
| pure closure | `zsh tools/run_closure.sh pure` | **11/11** |
| Python suite | `venv/bin/python -m pytest -q` | **268 passed, 1 declared skip** |
| lint | `venv/bin/ruff check --output-format=concise .` | clean |
| test manifest | `zsh tools/check_test_manifest.sh` | **121/121** — 85 Wolfram + 36 Python; 100 test / 15 producer / 6 quarantine |
| coverage ratchet | `venv/bin/python tools/check_coverage_ratchet.py` | global **31.74 %** against floor **31.73** |
| Wolfram tier + MUnit | `make ci-local` (pre-push hook) | **OK=72 FAIL=0 TOTAL=72 SCOPE=all** |
| glossary sync | `zsh tools/check_glossary_sync.sh` | exit 0 |

Coverage detail, from `coverage.json`: **61 files measured, 22 at 0 %,**
global 31.74 %. Module floors are declared for 30 of 61.

### 2.2 The commits that produced this state

| SHA | what it settled |
|---|---|
| `24c0965` | `D_v2` retired — it computed Shannon binary entropy over block densities |
| `dd1b9ba` | sumandos ruling (GLOSSARY §1d) gated |
| `a39b49f` | *pivot* retired as finance-only (GLOSSARY §1e); both measures reported side by side |
| `b2b5562` | bio artefacts regenerated; the simplicity claim does **not** survive |
| `9da02c1` | Wolfram-tier artefact refresh, verified to move only wall-clock |
| `20b2ae1` | syntax checker hardened; **two hypotheses about the stall falsified** |

### 2.3 The two comparison measures — and they are never merged

**Author directive, 2026-09-07.** The two measures are:

1. **Index-set program length** — owner `src/description_lengths.py`.
2. **BDM** — block decomposition method.

They are reported **side by side, under their own names, never combined into
one number**. Author decision #96 forbids a hybrid ("the cheaper of two
encodings with a selector bit" was proposed and rejected). Reporting two named
measures is not a hybrid; folding them into one number is.

`src/pipeline/Contingency_Monitor.py` returns **`UNDECIDED`** when the two
measures disagree on falsification. It does not silently pick one.

**Why both are needed, measured.** No single adjacency-only encoding of our
method survives every structured family (n = 16, matched edge count,
structured / random-mean in bits):

| family | row-run index-set | BDM |
|---|---|---|
| checkerboard | 1050.5 / 563.9 **inverted** | 34.3 / 489.9 ok |
| column stripes | 1050.5 / 568.4 **inverted** | 34.2 / 485.2 ok |
| 12-node chain vs 200 matched random | random called simpler 14/200 | 0/200 |
| schemata over index bits, chain | **200/200 inverted** | — |

BDM inverts on none of the probes; the index-set length inverts on alternating
structure. Hence both, named, never merged.

### 2.4 No Shannon quantity may be one of our measures

**Author directive #117, 2026-09-07.** Shannon survives **only** as an
explicitly labelled statistical *baseline* or *statistic*, never as one of our
complexity measures.

All 34 sites flagged `OURS` by `audit/AUDIT04_E_measures/census_shannon.py`
are adjudicated one by one in `GOVERNANCE/VERIFICATION.md` §5a: **0 forbidden
measures, 3 labelled baselines, 1 statistic, 30 false positives.**

The one statistic is `src/stats/Mutual_Information_Analyzer.py` (Kraskov
estimator via sklearn). It measures *dependence between a complexity score and
a clinical outcome*, exactly as a correlation does. Its payload carries
`'kind': 'statistic'` and `'is_complexity_measure': False`.

Note: `log2(C(n,k))` **enumerative** code lengths (in `HierarchyEncoder.py`,
`MotifEncoder.py`) are legitimate description lengths and are **not** Shannon.

### 2.5 A fact that constrains the design

**Σ_v D_schema is exactly invariant under degree-preserving rewiring.**
`schema_normal_form_length` prices a node from `(n, gate, in-degree)` alone,
and `degree_preserving_swap` preserves all three. Therefore this measure
returns an identical number for a real network and every one of its nulls.

**Our mechanism-side measure cannot answer a wiring question** — not because
it is weak, but because a wiring question is not what it measures. This is
pinned by a test in
`tests/analysis/test_complexity_measures_are_algorithmic.py` so that the
retired-`D_v2` forwarder is not repointed at it in six months.

### 2.6 The standing negative result

Over **231 networks × 1000 nulls**, regenerated at `b2b5562`:

- The median gap is **negative under both measures and all three nulls** — the
  median biological network is *longer* than the best of its 1000 nulls.
- Index-set: median gap **−27.68 / −31.26 / −38.05 bits**; beats every null in
  **53 / 34 / 39 of 231**.
- BDM: median gap **−59.20 / −53.12 / −68.45 bits**; beats every null in
  **14 / 7 / 10 of 231**.
- The two measures **disagree on 87 / 77 / 77 of 231**.

The superseded claim ("72–111 of 231 separate at two sigma") came from the
retired Shannon measure with a retired z-score, over an artefact regenerated by
nothing.

**This does not show the method is wrong. It shows this claim, over this corpus
and these nulls, is not supported.** Neither manuscript asserts it; `D_v2`
appears in neither.

### 2.7 Vocabulary: *pivot* is a finance term (GLOSSARY §1e)

The word names nothing in the Boolean indexing method. The method's six names
are: **connected inputs, essential variables, decimal anchor, decimal family,
free coordinates, sumandos**. Enforced by
`tools/check_glossary_conformance.sh`, which prints its denominator and
refuses (exit 2) on zero files.

Do **not** reintroduce it, including in ordinary-English action codes.

---

## 3. The two open defects

### 3.1 G1 — the pre-push hook stalled for three hours (INTERMITTENT, CAUSE UNKNOWN)

**Observation, 2026-09-08.** `git push origin fixing` ran the pre-push hook
(`core.hooksPath = githooks` → `make ci-local`). After **3 h 04 m**:

```
PID   ELAPSED   %CPU  TIME     COMMAND
25025 03:04:24  0.0   0:00.01  git push origin fixing
25036 03:04:23  0.0   0:00.01  make ci-local
25051 03:04:23  0.0   0:00.00  zsh tools/run_closure.sh wolfram
25054 03:04:23  0.0   0:01.27  WolframKernel -script tools/check_wolfram_syntax.wl
```

State `S`, **0.0 % CPU, 1.27 s of CPU accumulated**, stdin/stdout/stderr all
pipes. Nothing had been printed. The kernel had done roughly the right amount
of work (a full 156-file parse costs ~1.3 s CPU) and then sat idle for ever.

**Two hypotheses, both FALSIFIED. Do not spend time on them again.**

| hypothesis | test | verdict |
|---|---|---|
| A file in the tree is an *incomplete* expression, so `ToExpression` requests continuation input and blocks on the hook's stdin pipe | ran `SyntaxQ` over all in-scope files | **FALSE** — 156/156 parse, none incomplete |
| The success path falls off the end without `Exit`, so the kernel waits on stdin | restored the pre-fix script from `9da02c1`, ran under an open stdin pipe, with and without an appended `Exit[0]` | **FALSE** — exits in **6 s** either way |

**A methodological trap I fell into, recorded so it is not repeated.** I first
concluded "still hung" from a harness of the form
`( sleep 300 | kernel ; echo $? > rc )`. The `echo $?` waits for the **whole
pipeline**, and the pipeline contains the `sleep`, so the status could not
appear until the sleep ended. The kernel had exited long before. **Measure the
process, not the wrapper**: `pgrep -f 'WolframKernel.*<script>'`.

**It did not reproduce.** A second push at `20b2ae1` passed the same stage in
about ten seconds and the whole hook completed green. So the stall is
**intermittent**, which places it in the same family as G2 rather than being a
deterministic bug.

**What was fixed at `20b2ae1`** is a genuine latent defect, on its own merits
and **not** a fix for this stall:

- `ToExpression` conflated two failures. A **surplus** bracket `f[x]]` is an
  error and returns `$Failed` (exit 1, as intended). An **unclosed** bracket
  `f[x` is not an error but an *incomplete expression*: the parser consumed
  every character and still wants more, so it reads stdin — a pipe that never
  delivers under a hook. Such a file **would** hang the hook for ever, silently.
- `SyntaxQ` answers the same question and **cannot** request continuation.
  The incomplete case is classified by `SyntaxLength >= StringLength`.
- Every file is now **announced before it is parsed** (stderr, so stdout stays
  the machine-readable verdict). Three hours of silence naming no file is what
  made the stall undiagnosable.
- Verified by planting both shapes: `156/158`, `_plant_incomplete.wl` reported
  INCOMPLETE, `_plant_surplus.wl` reported "syntax error at character 4", and
  **no hang on the incomplete plant**.

> The fix broke itself once and the guard caught it: documenting the unclosed
> comment case meant writing `(*` literally, Wolfram comments **nest**, and the
> file was swallowed — executing nothing, printing nothing, exiting 0. That is
> exactly the silent-green failure the script was written in AUDIT03 to catch.
> **Never write a bare comment-opener inside a Wolfram comment.**

### 3.2 G2 — the exit-139 SIGSEGV (LIVE, base rate higher than recorded)

Kernels die with **exit 139 (SIGSEGV)** *after* completing their work. The
completion sentinel — written as each test's last expression, cleared by the
runner before each run — proves every line above it evaluated, so these are
scored as passes and reported loudly. That adjudication is sound and was
verified by planting (death before the sentinel → FAIL; death after → OK and
recorded; no sentinel on a clean exit 0 → FAIL). See `GOVERNANCE/VERIFICATION.md`
line 157 and `tests/MUnit/run-tests.sh:202–232`.

**The rate is not stable, and the recorded base rate is understated:**

| run | crashes | which |
|---|---|---|
| historical (VERIFICATION.md:157) | 3 in ~9 full-suite runs | `TSK-ARCH-006`, `NANDTests.m`, `TSK-GATES-001` |
| 2026-09-07, committed at `9da02c1` | **0** | — |
| 2026-09-08, at `20b2ae1` | **5 in one run** | `TSK-ALGO-002-LargeSample`, `KOFNNetworkTests`, `VerificationSamples`, `TSK-THEORY-003`, `TSK-NATURE-LEV3-SETUP-002` |

**The crashing set is different every time**, which argues against a defect in
any one test and for something in the kernel's shutdown path. Note that G1 and
G2 may share a cause: both are kernel-lifecycle faults that occur *after* the
science is done, one dying and one hanging.

---

## 4. Task G1 — obtain a definitive diagnosis of the stall

**Goal.** Either identify the cause with evidence, or establish a bounded,
principled mitigation that cannot mask a real failure.

**Dependencies.** None. Do this first: every other task in this plan is gated
on a hook that terminates.

**Why it matters.** The pre-push hook is the **only** thing that runs the
Wolfram tier; hosted CI has no kernel. A hook that hangs intermittently means
the Wolfram tier is unverifiable on an unpredictable fraction of pushes.

### Steps

**G1.1 — Instrument the closure runner to timestamp every member.**
Owner: `tools/run_closure.sh`. Enrich it (do not create a second script) to
print an ISO-8601 timestamp and elapsed seconds per member, to stderr.
*Output:* a stage-level timeline for every future run.

**G1.2 — Add a hard timeout per member, which FAILS rather than hangs.**
Owner: `tools/run_closure.sh`. Note `timeout(1)` is **not available on this
macOS shell** — use a watchdog subshell (`( sleep N; kill -TERM $pid ) &`) or
`perl -e 'alarm'`. On expiry the member must exit **non-zero with a named
stage**, never be skipped.
*Acceptance:* plant a deliberate `Pause[9999]` in a member; the runner must go
**red** within the timeout and name that member. Remove the plant; green.
*This is the mitigation that makes the hook safe even if the cause is never found.*

**G1.3 — Capture a stack sample the next time it stalls.**
Add to the watchdog, before killing: `sample <pid> 10 -file
/tmp/cb_stall_<stage>.txt` (macOS built-in) and `lsof -p <pid>`. A single
capture will show whether the kernel is blocked on `read(stdin)`, on a socket
(licence server), or in shutdown.
*Acceptance:* the artefact exists and is attached to the finding.

**G1.4 — Test the licence-contention hypothesis (the leading untested one).**
The kernel had done its work and idled at 0 % CPU with all three streams as
pipes. A plausible cause not yet tested is a **licence or front-end handshake
at shutdown** (MathLink/WSTP teardown, or `$Failed` on a licence check). Probe:
run the syntax member 30 times in a loop under an open stdin pipe, with a
second kernel running concurrently, and record the exit-time distribution.
*Acceptance:* a table of 30 exit times with the count of stalls, or a
statement that 0/30 stalled and the hypothesis is unsupported at that n.

**G1.5 — Decide `-script` versus `-noprompt -run`.**
Under `-script` the kernel reads the script from a file but its stdin is still
the inherited pipe. Test whether invoking with stdin explicitly closed
(`< /dev/null`) inside `run_closure.sh` changes the stall rate.
*Caution:* `< /dev/null` may mask a genuine "waiting for input" bug rather than
fix it. If it removes the stall, that is **evidence about the cause**, and must
be reported as such, not quietly adopted as a fix.

### Acceptance criteria for G1

- [ ] `tools/run_closure.sh` prints a per-member timeline with elapsed seconds.
- [ ] Every member has a timeout that produces a **named red**, verified by planting.
- [ ] A stall-capture path exists (`sample` + `lsof`), verified by planting.
- [ ] The licence-contention hypothesis is tested at n ≥ 30 and reported with its denominator.
- [ ] `GOVERNANCE/VERIFICATION.md` carries a row for the stall stating either the cause or, honestly, that it remains unknown and what is now guaranteed instead.

### Expected outputs

- Modified `tools/run_closure.sh` (one owner, enriched).
- A finding note at `audit/AUDIT04_G_stall/FINDING.md` with the 30-run table.
- One commit, message stating what was and was not established.

---

## 5. Task G2 — characterise the SIGSEGV properly

**Goal.** Replace an anecdotal base rate with a measured one, and decide
whether the sentinel adjudication remains sufficient.

**Dependencies.** G1.1 (timeline) helps but does not block.

### Steps

**G2.1 — Establish the rate.** Run the full MUnit suite **10 times**
(`make suite`, ~40 min each — run overnight, in background, with `--quiet`).
Record for each run: which tests crashed, exit code, and whether the sentinel
was present.
*Acceptance:* a table of 10 runs; the per-test crash frequency; the
distribution of crashes-per-run. State the denominator in every sentence.

**G2.2 — Test whether crashes are memory-ordered.** The historical note
mentions memory pressure. Record peak RSS per test and correlate with crash
frequency. **Report the correlation with its n and its null**, not as a
narrative.

**G2.3 — Decide the adjudication.** If the crash rate is stable and always
post-sentinel, the current "counted as a pass, recorded not hidden" ruling
stands and should be restated with the measured rate. If any crash is ever
found *before* the sentinel, that is a **P0** and the suite's green is void
until it is resolved.

### Acceptance criteria for G2

- [ ] 10 full-suite runs recorded, with the crash set per run.
- [ ] A measured crash rate replacing "3 in ~9" in `GOVERNANCE/VERIFICATION.md:157`.
- [ ] An explicit statement of whether a pre-sentinel death was ever observed.

---

## 6. Phase B — coverage Tier 1

**Goal.** Reduce the 22 modules at 0 % coverage, raising the ratchet as you go.

**Dependencies.** G1 (a hook that terminates) for the final push only; the work
itself runs in the pure tier.

**Current state (producer: `coverage.json`, `venv/bin/python -m pytest -q
--cov=src --cov-report=json` — note the **absent path argument**, see below):**
61 files measured, **22 at 0 %**, global **31.74 %**, floors declared for 30.

> **Trap, already sprung once.** `GOVERNANCE/COVERAGE_RATCHET.toml` used to
> prescribe `pytest -q tests/analysis/ --cov=src`. Following that produced
> 13.97 % against a floor of 29.12 % with 18 modules UNMEASURED — the file
> recording the floors was prescribing a partial denominator. It is corrected;
> **do not reintroduce a path argument.** `pytest.ini` and the root
> `conftest.py` already define the collection set from the manifest.

### Steps

**B.1** — Rank the 22 zero-coverage modules by *whether they carry a claim in a
manuscript or a governance document*. A module that produces no cited number is
lower priority than one that does. **Do not** simply take them alphabetically.

**B.2** — For each module in Tier 1, write tests that **bite**: verified by
planting a defect (an inverted comparison, an off-by-one, a dropped branch) and
observing red, then restoring and observing green. A test that passes against a
mock it defines itself is worthless — that exact defect was found twice in this
repository (AUDIT04-E).

**B.3** — Ratchet the floors up in the same commit. Floors are compared
**strictly**; floor **down** to two decimals (the file's existing convention),
because a floor at full float precision is a tripwire that fires on jitter.

**B.4** — Never lower a floor to accommodate new untested lines. When coverage
dipped 31.35 → 31.31 during AUDIT04-F, the resolution was to **extract the
logic-carrying part to module level and test it**, not to lower the floor.

### Acceptance criteria for Phase B

- [ ] Tier 1 modules identified by a stated ranking rule, not by convenience.
- [ ] Every new test verified by planting; the plant and its result recorded in the commit message.
- [ ] Global floor raised; no per-module floor lowered.
- [ ] `venv/bin/python tools/check_coverage_ratchet.py` green.

---

## 7. Phase D — mutation testing

**Goal.** Extend the mutation catalogue to the modules newly covered by Phase B,
and widen thin margins.

**Dependencies.** **Phase B must land first** — mutants on uncovered code
measure nothing.

**Current state (producer: `audit/AUDIT03_R2_collapse/MUTATION.md`):**
semantic kill rate **23/25 = 92.0 %**; unit-test kill rate **19/25 = 76.0 %**.
Two owners have zero unit-test kills. The catalogue grew from 25 to 30 in
Phase A (five new `deconvolution` mutants).

### Steps

**D.1** — Add mutants for each module Phase B brought above 0 %, following the
existing catalogue's three classes (semantic / structural / cosmetic). Semantic
is the class that matters: it changes an *answer*.

**D.2** — For each mutant, record the **prediction before running it**. The
existing document does this and it is what makes the result evidence rather
than a scoreboard.

**D.3** — Report both rates separately. The gap between the semantic rate
(92.0 %) and the unit-test rate (76.0 %) is the honest measure of the
instrument, and collapsing them into one number destroys the finding.

### Acceptance criteria for Phase D

- [ ] Every newly covered module has ≥ 1 semantic mutant.
- [ ] Predictions recorded before execution.
- [ ] Both kill rates reported with their denominators; no merged figure.

---

## 8. Phase E — ledger and tag

**Goal.** Close AUDIT04 with a verifiable record and a tag.

**Dependencies.** G1, G2, Phase B, Phase D.

### Steps

**E.1** — Reconcile `GOVERNANCE/VERIFICATION.md` end to end. Every row must
name its producer and its denominator. Run
`tools/check_verification_numbers.py`.

**E.2** — **T0.4 from the master plan: branch reconciliation.** `CLAUDE.md`
currently states that the live branch is `clean` and that `main` is stale by
policy until T0.4 retags it. **That statement is now wrong** — the live branch
is `fixing`. Reconcile `fixing` → `clean` → `main`, retag, and correct
`CLAUDE.md` in the same commit.

**E.3** — Tag the audit close. Record in the tag message the measured state:
closure, suite, manifest, coverage, and the **open** items (G1 if unresolved,
G2's measured rate).

**E.4** — Update the memory index at
`~/.claude/projects/-Users-alberto-Documents-projects-CausalBool/memory/MEMORY.md`.

### Acceptance criteria for Phase E

- [ ] `CLAUDE.md` branch statement corrected.
- [ ] `main` reconciled and retagged.
- [ ] Tag message states the measured state **and** what remains open.

---

## 9. Open question, unresolved

**The coverage ratchet's unit.** The ratchet compares **percentages**. A
percentage moves when the denominator moves — adding a new uncovered module
lowers the global figure without any regression in tested behaviour. A
statement-count floor would not have that property. This has been noted twice
and never decided. **It is an author decision, not an implementation choice.**

---

## 10. Standing constraints — these override any instinct to do otherwise

1. **No Claude co-authorship.** Every commit uses
   `git -c user.name="Alberto" -c user.email="albertohernandezespinosa@gmail.com"`.
   No `Co-Authored-By`, no tool attribution.
2. **British English, no contractions.** Flowing scientific prose, direct but
   elegant; it must read as human, not AI-generated.
3. **No hybrid measure** (decision #96). Two named measures, side by side.
4. **No Shannon quantity as one of our measures** (directive #117).
5. **Replication packages (`imp-*`) are NOT converted to our measure** — that
   would make the replication unfaithful.
6. **The `.pth` file in `venv` belongs to a sibling repository and is not
   edited.** It injects two sibling repos and one name (`data`) collides;
   `conftest.py` puts `src/` first on `sys.path` to compensate.
7. **`doc/` and `workspaces/` are provenance archives.** Do not rewrite them.
8. **`src/external/ccapi/` is vendored.** Dependency boundary; do not modify.
9. **Superseded scripts go to `archive/`,** not deleted, to preserve provenance.
10. **`GOVERNANCE/GLOSSARY.md` is a COPY.** The canonical source is
    `~/Documents/projects/series-deconvolution/GLOSSARY.md`. Amend the sibling,
    then re-sync; `tools/check_glossary_sync.sh` goes red on a local edit.
11. **Find the owner before writing code** (the `monolithic-code` law). Search
    by **body fragment**, not by name. Default resolution is *enrich the owner*.
    Any new definition ships with the guard that keeps it single, verified by
    **planting a copy** in the same commit.
12. **Delegation to external agents is stopped** unless the author reinstates it.

---

## 11. Verification block — run before every push

```bash
cd /Users/alberto/Documents/projects/CausalBool
source venv/bin/activate

zsh tools/check_glossary_sync.sh            # exit 0
zsh tools/check_glossary_conformance.sh     # prints its denominator; refuses on 0
zsh tools/check_test_manifest.sh            # 121/121, BOTH languages non-zero
venv/bin/python -m pytest -q                # no path argument, by design
venv/bin/ruff check --output-format=concise .
zsh tools/run_closure.sh pure               # 11/11
venv/bin/python tools/check_coverage_ratchet.py
venv/bin/python tools/snapshot_paper_numbers.py --check

# Wolfram tier — the pre-push hook is the ONLY thing that runs it (~40 min).
# CI cannot: hosted runners have no kernel.
make ci-local
```

**Wolfram kernel invocation (confirmed working):**

```bash
HOME=/Users/alberto /Applications/Wolfram.app/Contents/MacOS/WolframKernel -script <absolute-path>
```

The flag is `-script` (not `-noprompt -script`, not `-file`); the `HOME=`
prefix is **required**. `$ScriptCommandLine` is **empty** under `-script` —
pass arguments via environment variables.

**Verify a push against the remote ref, never against the notification:**

```bash
git fetch -q origin && git rev-parse HEAD origin/fixing   # must be identical
```

Background-task notifications report the **wrapper's** exit code. `$?` after a
pipe returns the **last** command's status. Both have produced false "success"
readings in this repository.
