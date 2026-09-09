# AUDIT04-H — the comparator, the two measures, and the kernel lifecycle

**Status:** open — governing document for the remainder of AUDIT04.
**Branch:** `fixing`
**Written:** 2026-09-08
**Anchor commit:** `af7690e`
**Author:** Alberto Hernández Espinosa
**Supersedes:** `plans/AUDIT04-G_stall_and_completion.md`. Every open item of that
plan is carried forward here, four of its acceptance criteria are rewritten
because they could pass while the thing they guard was still broken, and one of
its stated facts (the mutation rate, §7) is measurably out of date. G remains on
disk as provenance; it is not executed.
**Master plan:** `AUDIT_FIXING_PLAN_01.md` closed itself at its own close-out
entry (line 1775: *"This plan now holds NO open items"*) and handed authority to
`SUCCESSOR_PLAN_R4.md`. That succession was never recorded in `CLAUDE.md` or in
plan G. Task H0.4 settles it.

---

## 0. How to read this document

This plan is written for an agent with **no memory of any previous session**.
Everything needed to act is stated here or named by path. Where a number
appears, its **producer** is named and the **date and commit it was measured at**
are given, because a number without a producer drifts, and that has now happened
four times in this repository.

### The three standing laws

1. **Measure, do not assert.** Every claim of the form *X is clean / X agrees /
   X is fixed* names the command that produced it and the denominator it ran
   over. `all match: True` over zero cases is the failure this project exists to
   stop.
2. **No number without its reference distribution in the same sentence.**
3. **Locate the owner before anything is written.** One core per concept, found
   by **body fragment**, never by name. The default resolution to a gap is to
   enrich the owner.

### The fourth law, which this plan establishes

4. **No headline statistic without its response to the parameters it is not
   about.** A statistic that moves monotonically in a knob of its own producer —
   the number of nulls drawn, the seed, the node labelling — is a measurement of
   that knob and may not be the headline. This law is added because the three
   above do not catch the defect in §2.1: the quantity concerned has a
   denominator, has a reference distribution, has a declared owner and a declared
   null, and is still wrong. Task H2.4 writes it into `GOVERNANCE/NULLS.md`,
   which already owns the neighbouring rule for null models.

---

## 1. Confirmed state at `af7690e`

### 1.1 Carried from plan G, not re-measured in this session

These seven rows stand on plan G's authority, measured 2026-09-08 at `20b2ae1`.
Re-run them before trusting them; the Wolfram tier alone costs about 40 minutes.

| gate | command | recorded result |
|---|---|---|
| pure closure | `zsh tools/run_closure.sh pure` | 11/11 |
| Python suite | `venv/bin/python -m pytest -q` | 268 passed, 1 declared skip |
| lint | `venv/bin/ruff check --output-format=concise .` | clean |
| test manifest | `zsh tools/check_test_manifest.sh` | 121/121 — 85 Wolfram + 36 Python |
| coverage ratchet | `venv/bin/python tools/check_coverage_ratchet.py` | global 31.74 % against floor 31.73 |
| Wolfram tier + MUnit | `make ci-local` | OK=72 FAIL=0 TOTAL=72 SCOPE=all |
| glossary sync | `zsh tools/check_glossary_sync.sh` | exit 0 |

### 1.2 Measured fresh on 2026-09-08 at `af7690e`

Each row below was produced by the named command during the review that
generated this plan. Where it contradicts plan G, this table wins.

| what | measured | producer | contradicts |
|---|---|---|---|
| mutation kill rates | **30/30 semantic, 30/30 unit-test, 0 survivors, no owner below 3/3** | `venv/bin/python audit/AUDIT03_R2_collapse/mutation_harness.py --report` | plan G §7, which states 23/25 and 19/25 and "two owners have zero unit-test kills" |
| mutation results staleness | results recorded at `f2c2f77`, **34 commits behind `af7690e`**, printed with no warning | same command; `git rev-list --count f2c2f77..HEAD` | nothing; this is undeclared |
| verification-numbers gate | **checked 12 of 44** numeric claims; 32 named unchecked | `venv/bin/python tools/check_verification_numbers.py` | `GOVERNANCE/VERIFICATION.md` §3 prose, which says "29 numeric rows … names the 17 it does not" |
| branch geometry | `main` `e358272` · `clean` `c5c08ca` · `fixing` `af7690e`; `fixing` is **115 ahead of and 7 behind** `main`; `clean` is a **strict ancestor** of `fixing` (179 behind, 0 ahead) | `git rev-list --count` | `CLAUDE.md:41` ("live branch `clean`"); `MEMORY.md` ("`clean` holds the scientific work") |
| tags | `audit01-baseline` @ `366d771`, `audit01-closed` @ `6f56ea9` | `git rev-parse` | plan G §8 E.2, which assigns T0.4 as remaining work when T0.4 is done |
| dead manuscript path | `CLAUDE.md:126` points at `papers/method/manuscript/method_paper.tex`, which does not exist | `grep -n` | AC-1.4c of the master plan, recorded satisfied at `316ce22` |
| kernel crash reports on disk | **25** `WolframKernel` reports; **23** share one signature (SIGSEGV, faulting **thread 10**, pthread from `libWolframRTL_Kernel.dylib`, faulting frames in unnamed JIT memory); **2** differ (thread 0, `mathlink` frames); no spin or hang report exists | `~/Library/Logs/DiagnosticReports/` | `VERIFICATION.md:157`, which states the kernel "dies at SHUTDOWN" |

### 1.3 The bio artefact, recomputed from disk

`results/bio/null_stats.json` holds **231 records, 1000 nulls per type**. Every
figure published in `VERIFICATION.md` §5b reproduces exactly. The arithmetic is
not in question. Two further columns, computed from the same file during this
review, are:

| measure × null | median gap vs **best of 1000** (published) | networks beating all 1000 | median gap vs **median null** | networks shorter than median null | median permutation tail `exceed` |
|---|---|---|---|---|---|
| index-set, ER | −27.68 | 53/231 | **+25.22** | **171/231** | 0.130 |
| index-set, degree | −31.26 | 34/231 | **+10.72** | **149/231** | 0.257 |
| index-set, gate | −38.05 | 39/231 | **+9.29** | **147/231** | 0.296 |
| BDM, ER | −59.20 | 14/231 | **+3.35** | **150/231** | 0.340 |
| BDM, degree | −53.12 | 7/231 | **+1.09** | **130/231** | 0.395 |
| BDM, gate | −68.45 | 10/231 | **+1.39** | **131/231** | 0.423 |

---

## 2. Why this plan exists

Plan G closes AUDIT04 on two kernel-lifecycle defects. Those are real and are
carried forward as H3 and H4. But two defects of larger consequence sit upstream
of them, in the science rather than the infrastructure, and plan G does not name
either.

### 2.1 The standing negative result is a property of its comparator

`gap_bits` is defined in the owner as `min(nulls) − D(bio)`
(`src/experiments/Null_Generator_HPC.py:133`), so it compares the real network
against the **minimum of 1000 draws**. Three consequences, all measured on
2026-09-08 over the 231-record artefact:

- **Its sign carries no more information than a threshold.** `gap_bits > 0` is
  exactly the event `exceed == 0`, in **231/231 records in all six measure × null
  cells**. It is a binary event at p < 1/1000 presented as a continuous quantity
  in bits, and its magnitude measures how far the minimum of the null ensemble
  sits below the real network — a property of the ensemble, not of the network.
- **It moves with a knob.** The minimum of N draws falls monotonically in N, so
  the published median gap becomes more negative simply by drawing more nulls.
  H1.1 measures this and states the size of the effect.
- **The sign reverses under a knob-free comparator.** Against the **median**
  null, the median gap is positive in all six cells, and a majority of networks
  is shorter than its median null in all six (table §1.3). The permutation tail
  already stored in the artefact says the median network is shorter than 87.0 %
  of its ER nulls under the index-set length and 57.7 % of its gate-preserving
  nulls under BDM.

`VERIFICATION.md` §5b concludes that "the median biological network **is not
simpler** than its randomised controls". That is what the best-of-1000 comparator
says. It is not what the artefact says. The retired two-sigma claim was rightly
retired; its replacement overshoots in the opposite direction by the same failure
class — a statistic chosen without regard to what it responds to.

**This plan does not reinstate the simplicity claim.** It requires the result to
be re-reported under all three comparators with the reference distribution
stated, and leaves the scientific reading to the author (decision **H-D1**).

### 2.2 "The index-set program length" names two different quantities: Variant A vs Variant E

`GOVERNANCE/DESCRIPTION_LENGTHS.md` names five variants. Two matter here:

- **Variant A**, `row_run_index_set_length` — a run-length code over the rows of
  an adjacency matrix. Canonical implementation credited to
  `imp-causalNet-paper/.../causalbool_mirror`; wrapper in the owner.
- **Variant E**, `schema_normal_form_length` (`D_schema`) — declared **the
  primary mechanism-side measure since AUDIT03/R3**, and named as such in
  `CLAUDE.md`.

The measurement uses Variant A: `results/bio/null_stats.json` records
`measure: "index_set_program_length"`, and
`tests/analysis/test_complexity_measures_are_algorithmic.py:186` binds the
`index_set` measure to `row_run_index_set_length`. Variant E appears in neither
reported measure. It is exercised only for rewiring-blindness and for XOR-versus-OR
separation.

Two consequences:

- **The §2.5 constraint of plan G is applied to the wrong measure.** The
  statement *"Σ_v D_schema is exactly invariant under degree-preserving rewiring,
  therefore our mechanism-side measure cannot answer a wiring question"* is true
  of Variant E. It is false of Variant A, which is fully blind under
  degree-preserving rewiring on **3 of 231 networks** (BDM: 2 of 231).
- **Both reported measures price a nuisance dimension neither has declared.**
  Measured 2026-09-08 with the owner's own functions, over 200 node relabellings
  — an isomorphism that changes no information:

  | object, n = 16 | Variant A spread | BDM spread |
  |---|---|---|
  | random, p = 0.2 | **98.10 bits** | **92.46 bits** |
  | chain | 0.00 (invariant) | **133.84 bits** |
  | hub | 0.00 (invariant) | 1.44 bits |

  Re-running the programme's own chain probe in a common coordinate (n = 12,
  11 edges, 200 chain draws against 200 matched random draws):

  | chain presented as | Variant A: random called simpler-or-equal | BDM: random called simpler-or-equal |
  |---|---|---|
  | canonical labelling, as stored | 9.5 % | **0.0 %** |
  | randomly relabelled | 9.5 % | **66.9 %** |

  Under relabelling BDM's chain cost moves 74.53 → 194.00 ± 18.47 bits, above the
  matched-random mean of 180.09 ± 19.78. The evidence that retired `D_v2` and
  that justifies *"BDM inverts on none of the probes"* holds only while the chain
  is handed to BDM in its canonical order.

**This does not overturn the bio result**, because the degree- and
gate-preserving nulls hold node identities fixed, so real and null are
label-matched there. It overturns the **argument** for the two-measure policy,
and it means the checkerboard inversion declared in `DECLARED_INVERSIONS` is not
a quirk to be declared but a symptom of a code that charges bits for a labelling.

Decision #96 (no hybrid) is **not** the obstacle to a single measure and is not
reopened by this plan. The obstacle is that neither reported measure prices an
isomorphism class. Author decision **H-D2** settles what follows.

---

## 3. Standing constraints — these override any instinct to do otherwise

Carried unchanged from plan G §10, and binding.

1. **No Claude co-authorship.** Every commit uses
   `git -c user.name="Alberto" -c user.email="albertohernandezespinosa@gmail.com"`.
   No `Co-Authored-By`, no tool attribution.
2. **British English, no contractions.** Flowing scientific prose, direct but
   elegant; it must read as human, not as machine-generated.
3. **No hybrid measure** (author decision #96). Two named measures, side by side,
   never folded into one number.
4. **No Shannon quantity as one of our measures** (directive #117). Labelled
   baselines and statistics are permitted and must say what they are.
5. **Replication packages (`imp-*`) are never converted to our measure.**
6. **The `.pth` file in `venv` belongs to a sibling repository and is not edited.**
7. **`doc/` and `workspaces/` are provenance archives.** Do not rewrite them.
8. **`src/external/ccapi/` is vendored.** Dependency boundary; do not modify.
9. **Superseded scripts go to `archive/`,** never deleted.
10. **`GOVERNANCE/GLOSSARY.md` is a copy.** Canonical source is the sibling
    `series-deconvolution`; amend there, then re-sync.
11. **Find the owner before writing code.** Search by body fragment. Default
    resolution is *enrich the owner*. Any new definition ships with the guard that
    keeps it single, verified by planting a copy in the same commit.
12. **Delegation to further agents is stopped** unless the author reinstates it.
13. **The word *pivot* is finance-only** (GLOSSARY §1e). Do not reintroduce it,
    including in ordinary-English action codes.

---

## 4. Engineering expectations — the uniform contract for every task below

These apply to every task and are not restated in the cards.

**Before writing any code**, answer the four `monolithic-code` questions out
loud in the commit message or the finding note: where is the core that owns this
concept; does it already exist under another name, searched by body fragment;
why does a new definition beat enriching the owner; what guard keeps it single.
Every task card below names its owner. If the named owner turns out to be wrong,
**stop and say so** rather than creating a second one.

**Every guard, without exception:** refuses on empty input, prints its
denominator, exits non-zero on failure, and has been verified by planting the
defect and watching it go red. The plant and its result go in the commit message.

**Every number written anywhere** — a document, a commit message, a finding note
— carries its producer and its denominator in the same sentence, and its
reference distribution where one exists.

**Bracketing.** Any task touching Wolfram or the manuscripts runs the relevant
gate before the first edit and after the last, and records both readings.

**Commits.** One commit per task, message prefix `[AUDIT04-H/<task-id>]`, pushed
after each task. The message states what was established **and what was not**.
Verify a push against the remote ref, never against the notification:
`git fetch -q origin && git rev-parse HEAD origin/fixing` must be identical.

**Stop rules.** Three conditions halt a task and require the author before it
resumes: an author-decision gate is reached; the named owner is wrong; a
measurement contradicts a fact stated in §1 of this plan. Log the halt with its
evidence; do not improvise past it.

**Scope discipline.** Defects discovered mid-task are logged as candidates in the
task's finding note and fixed under their own task, unless they block the current
acceptance criterion.

**Two traps already sprung in this repository, recorded so they are not sprung
again.** Measure the process, not the wrapper: `$?` after a pipeline returns the
last command's status, and a background-task notification reports the wrapper's
exit code. Both have produced false readings of success here. And never write a
bare comment-opener inside a Wolfram comment: comments nest, and the file is
swallowed — executing nothing, printing nothing, exiting 0.

---

## 5. The tasks

Effort scale: **S** ≤ 2 h · **M** half a day · **L** 1–2 days.

---

### H0 — Correct the record (S, no science, unblocks the rest)

**Goal.** Bring four documents into agreement with what the tools print, so that
no later task inherits a false premise. Nothing in this task requires judgement.

**Owners.** `plans/AUDIT04-G_stall_and_completion.md`,
`GOVERNANCE/VERIFICATION.md`, `CLAUDE.md`,
`audit/AUDIT03_R2_collapse/mutation_harness.py`,
`~/.claude/projects/-Users-alberto-Documents-projects-CausalBool/memory/MEMORY.md`.

**Pre-requirements.** Clean working tree at `af7690e`; `venv` active.

**Steps.**

**H0.1 — the mutation rate.** Run
`venv/bin/python audit/AUDIT03_R2_collapse/mutation_harness.py --report` and
record its output verbatim. Add a supersession header to plan G stating that it
is superseded by this document and that its §7 figures (23/25, 19/25) are stale.
Correct `MEMORY.md`'s `audit04-testing-instrument` entry to the measured pair,
with its date and the SHA the results were recorded at.

**H0.2 — the staleness contract.** Enrich `mutation_harness.py` so `--report`
compares the stored `head_sha` against the current HEAD and prints, on its first
line, either `results are current at <sha>` or
`WARNING: results recorded at <sha>, HEAD is <sha>, N commits behind`. It must
not silently print a stale rate. The existing SHA check at line 424 guards the
resume path only; enrich it, do not add a second one. *Verified by planting:*
run `--report` at HEAD and after one dummy commit; the second run must print the
warning.

**H0.3 — the page that checks itself.** `VERIFICATION.md` §3 says the gate covers
"29 numeric rows … names the 17 it does not"; the gate prints 12 of 44 with 32
unchecked. Correct the prose. Then enrich `tools/check_verification_numbers.py`
so that these three counts in the prose are themselves checked against what the
gate computes — the defect is that a gate parsing table rows left the sentence
*about the gate* unguarded. *Verified by planting:* alter one of the three
numbers in the prose; the gate must exit non-zero naming it.

**H0.4 — the two stale statements in `CLAUDE.md` and the plan lineage.** Correct
`CLAUDE.md:126` to the two real manuscript paths, and `CLAUDE.md:41` to the
measured branch geometry of §1.2. Add one paragraph to `CLAUDE.md` naming the
plan lineage: `AUDIT_FIXING_PLAN_01` closed and handed authority to
`SUCCESSOR_PLAN_R4.md`; `SUCCESSOR_PLAN_R4.md` Wave 0 (ORDERING §7 migration,
F36 exception coverage) is **open and out of scope for AUDIT04**; this plan
governs AUDIT04 to its close.

**Post-conditions.** No document in the repository states a mutation rate, a
gate coverage fraction, a manuscript path or a live branch that disagrees with
the tools.

**Acceptance criteria.**
- [ ] `mutation_harness.py --report` prints a staleness line; both states demonstrated by planting.
- [ ] `tools/check_verification_numbers.py` exits 0, and exits non-zero on a planted change to its own three self-describing numbers.
- [ ] `grep -rn "papers/method/manuscript/" CLAUDE.md` returns nothing.
- [ ] `grep -n "23/25\|19/25" plans/ *.md GOVERNANCE/` returns only text explicitly labelled superseded.
- [ ] `CLAUDE.md` names the plan lineage and the out-of-scope successor Wave 0.

**Outputs.** One commit. No finding note required; the commit message is the record.

---

### H1 — Re-report the bio result under all three comparators (M)

**Goal.** Replace a headline that measures the null ensemble's minimum with a
report that states what the artefact contains. **This task does not change the
science; it changes which number is quoted, and it publishes the ones that were
computed and never reported.**

**Owner.** `src/experiments/Null_Generator_HPC.py` — `separation()` at line 107
already returns `best_null` **and** `median_null`, and the summary block at lines
363–411 reports only the best-null comparator. This is an enrichment of roughly
thirty lines in one file. The consumer is
`src/experiments/SimplicityV2_Nature.py`; the decision rule is
`src/pipeline/Contingency_Monitor.py`.

**Dependencies.** H0.

**Pre-requirements.** `results/bio/null_stats.json` present, 231 records,
`nulls_per_type` 1000. Confirm both by reading the file before starting.

**Steps.**

**H1.1 — measure the knob (this is the evidence that retires the headline).**
Pre-register the prediction in the finding note **before running**: the median
gap against the best null becomes monotonically more negative as the null count
rises, while the median permutation tail `exceed` and the median-null comparator
do not. Then re-run the null generator over a **stated subsample** — 30 networks
chosen by a stated rule, seed pinned and recorded — at `nulls_per_type ∈ {10,
100, 1000}`, and tabulate all three comparators at each. Report the table with
its denominators. **A full 231-network re-run is not required and should not be
done**; the point is the direction and magnitude of the knob effect.

**H1.2 — publish the comparator that does not move with the knob.** Enrich the
summary block so it emits, per measure × null: median gap against best null
(retained, relabelled *worst-case advantage*), median gap against median null,
the count of networks shorter than their median null, the median `exceed`, and
the count at `exceed == 0`. **No recomputation of the nulls is required** —
`median_null` is already stored per record. Verify that the six published
best-null figures are byte-identical before and after, so the enrichment is
demonstrably additive.

**H1.3 — state the reference distribution for the tail.** The count of networks
at `exceed == 0` has never been reported against an expectation. Under
exchangeability of a network with its own nulls, `P(exceed == 0) = 1/1001`, so
the expected count over 231 networks is 0.23. Emit, beside each count, that
expectation and the exact binomial upper-tail probability. Values computed during
review, for cross-check: 53/34/39 (index-set, ER/degree/gate) and 14/7/10 (BDM)
against 0.23 expected, exact upper-tail p = 5.4 × 10⁻¹⁰⁷, 4.8 × 10⁻⁶², 2.0 × 10⁻⁷³,
7.6 × 10⁻²¹, 5.2 × 10⁻⁹, 7.9 × 10⁻¹⁴. Your run must reproduce these or explain
the difference.

**H1.4 — rewrite `VERIFICATION.md` §5b.** Replace the single-comparator table
with the full one. The prose must state, in this order and with denominators:
what the best-null comparator says; that its sign is exactly the `exceed == 0`
indicator (231/231, all six cells) and that it moves with the null count by the
amount measured in H1.1; what the median-null comparator says; what the
permutation tail says; and what the tail count says against its expectation.
**Do not write a conclusion about biology.** The reading is author decision
**H-D1**; until it is taken, the section states the measurements and says the
interpretation is open.

**H1.5 — flag, do not change, the decision rule.** `Contingency_Monitor.py`
falsifies on `gap` and `exceed` together. Whether the `gap` arm should move to
the median-null comparator is part of **H-D1**. Record the question in the
finding note with the measured consequence — how many of the 231 networks change
verdict under each rule — and change nothing until the author decides.

**Post-conditions.** Every comparator computable from the artefact is published;
no comparator is presented as *the* result; the interpretation is explicitly open.

**Acceptance criteria.**
- [ ] The H1.1 prediction is committed **before** the run that tests it; commit order is checkable in history.
- [ ] The knob table exists at three null counts with its subsample rule and seed stated, and the direction of the effect is reported whether or not it matches the prediction.
- [ ] The six previously published best-null figures are unchanged, demonstrated by a before-and-after diff in the commit message.
- [ ] Every count in §5b carries its denominator, and every tail count carries its expectation and exact p in the same sentence.
- [ ] `VERIFICATION.md` §5b contains no conclusion about biological simplicity in either direction.
- [ ] `tools/check_verification_numbers.py` covers at least the six median-null figures and the six tail counts; planted changes to them go red.
- [ ] The verdict-change count for the `Contingency_Monitor` question is measured and recorded; no behaviour is changed.

**Outputs.** One commit. Finding note at `audit/AUDIT04_H_comparator/FINDING.md`
carrying the pre-registered prediction, the knob table, the full six-cell table
under three comparators, and the open question for H-D1.

**Risks and stop rule.** If the knob measurement shows the median gap **not**
moving with the null count, the argument in §2.1 is weakened and the task
halts for the author — that would be a falsification of my reasoning and must be
reported as such, not smoothed over.

---

### H2 — The two measures: declare what they respond to (M/L)

**Goal.** Establish, by measurement, what each reported measure charges bits
for; correct the argument that justifies reporting both; and name the variants
so that two different quantities stop sharing one label.

**Owners.** `src/description_lengths.py` (the measures — **do not add a measure**),
`tests/analysis/test_complexity_measures_are_algorithmic.py` (the ordering
properties and `DECLARED_INVERSIONS`), `GOVERNANCE/NULLS.md` (the declaration
rule), `GOVERNANCE/DESCRIPTION_LENGTHS.md` and `GOVERNANCE/VERIFICATION.md` (the
naming).

**Dependencies.** H0. Runs in parallel with H1.

**Steps.**

**H2.1 — the response profile.** For each of the two reported measures, measure
the response to **node relabelling** — an isomorphism that changes no
information — over a stated set of structured families and random graphs, with
the number of relabellings and the seed stated. Report the spread in bits per
family per measure. Values from the review, for cross-check (n = 16, 200
relabellings): random p = 0.2 → Variant A 98.10, BDM 92.46; chain → Variant A
0.00, BDM 133.84; hub → Variant A 0.00, BDM 1.44.

**H2.2 — re-run the structured-family probes in a common coordinate.** The
existing probes compare a canonically labelled structured object against randomly
generated random graphs. Re-run them with the structured object **randomly
relabelled**, matched draw for draw. Report both the old and the new figure side
by side; neither replaces the other, because the old one is the declared
inversion's evidence and the reader must see what changed. Review values for
cross-check (n = 12, 11 edges, 200 × 200): canonical — Variant A 9.5 %, BDM
0.0 %; relabelled — Variant A 9.5 %, BDM **66.9 %**.

**H2.3 — adjudicate `DECLARED_INVERSIONS`.** The declaration currently reads the
checkerboard inversion as a property of a run-length code. If H2.1 shows the
inversion co-occurs with a labelling response, the declaration is incomplete and
must say so. Two arms are permitted: keep the declaration and add the response
profile beside it, or withdraw the family from the probe set as
label-confounded. **Both arms require the measurement first.** Whichever is
chosen, the guard must still go red if a declared inversion silently disappears.

**H2.4 — write the fourth law.** Enrich `GOVERNANCE/NULLS.md` — which already
owns *"declare what the statistic responds to before running a null"* — with the
symmetric rule for statistics reported outside a null test: **a headline
statistic is published together with its response to the run parameters it is
not about** (null count, seed, node labelling), and a statistic that moves
monotonically in one of them may not be the headline. Cite two case studies, both
from this repository and both measured: `gap_bits` against the null count (H1.1),
and the two measures against node labelling (H2.1). Do **not** create a new
governance file; this is the owner.

**H2.5 — name the variants.** Every place that says *the index-set program
length* must say which variant. At minimum: `VERIFICATION.md` §3 and §5b,
`DESCRIPTION_LENGTHS.md`, the `measure` key written into
`results/bio/null_stats.json` by the owner, and `MEMORY.md`. State explicitly, in
`DESCRIPTION_LENGTHS.md`, that Variant E (`D_schema`) is the declared primary
mechanism-side measure and appears in **neither** reported comparison measure,
and that the degree-preserving invariance property belongs to Variant E and not
to Variant A (measured: Variant A fully blind on 3 of 231 networks, BDM on 2 of
231). Regenerating the artefact solely to change a string is **not** required;
if the key is only corrected going forward, say so where the key is documented.

**Post-conditions.** Each reported measure has a published response profile; the
argument for reporting both rests on a label-matched comparison; no document uses
one name for two variants.

**Acceptance criteria.**
- [ ] Response profile published for both measures, with families, relabelling count, seed and denominators stated.
- [ ] Both the canonical and the label-matched probe figures appear side by side; neither is deleted.
- [ ] `DECLARED_INVERSIONS` adjudicated by one of the two permitted arms, with the measurement cited; the guard still goes red when a declared inversion disappears, verified by planting.
- [ ] `GOVERNANCE/NULLS.md` carries the fourth law with two measured case studies; no new governance file created.
- [ ] `grep -rn "index-set program length"` over `GOVERNANCE/` and `plans/` returns only occurrences carrying a variant letter.
- [ ] `venv/bin/python -m pytest -q` green; coverage ratchet not lowered.

**Outputs.** One or two commits. Finding note at
`audit/AUDIT04_H_measures/FINDING.md`.

**Risks and stop rule.** If the label-matched probe shows BDM **not** inverting
on the relabelled chain, §2.2's argument fails and the task halts for the
author. Report the contradiction plainly; my figure is 66.9 % over my own
sampler and it is yours to falsify.

---

### H3 — The intermittent stall: diagnosis or a bounded guarantee (M)

**Goal.** Either identify the cause of the three-hour pre-push hang with
evidence, or install a mitigation that cannot mask a real failure — and state
honestly which of the two was achieved.

**Owner.** `tools/run_closure.sh`. Enrich it; do not create a second runner.

**Dependencies.** H0. Do this before H4 — every full-suite run is gated on a
hook that terminates.

**Two hypotheses are already falsified. Do not re-test them.** A file in the tree
being an incomplete expression: false, 156/156 parse. The success path falling
off the end without `Exit`: false, exits in 6 s either way. A third fact from this
review: **no macOS spin or hang report exists for any WolframKernel**, so a
blocked kernel leaves no artefact of its own and the watchdog capture below is
the only route to evidence.

**Steps.**

**H3.1** — Print an ISO-8601 timestamp and elapsed seconds per closure member, to
stderr, so a future stall names the stage it is in.

**H3.2** — Add a per-member watchdog that produces a **named red**, never a skip.
`timeout(1)` is not available on this shell; use a watchdog subshell or
`perl -e 'alarm shift @ARGV; exec @ARGV or die'` — note the idiom, because
`perl -e 'alarm $ARGV[0]; exec @ARGV'` silently no-ops the exec on this platform
and has already produced a whole superseded baseline in this repository.

**H3.3** — Before killing, capture `sample <pid> 10 -file /tmp/cb_stall_<stage>.txt`
and `lsof -p <pid>`. This is the only evidence path that exists.

**H3.4** — Test the licence-contention hypothesis: run the syntax member 30 times
under an open stdin pipe with a second kernel running concurrently, and record
the exit-time distribution.

**Acceptance criteria.** *(Four of these are rewritten from plan G, which could
have passed each while the defect remained.)*
- [ ] A per-member timeline with elapsed seconds is printed on every run.
- [ ] The per-member timeout is set to a stated multiple of the **measured** p99 wall-clock for that member, the measurement is named, and the plant fires **at the production value** — not at a value lowered for the test.
- [ ] The stall-capture path is verified by planting a `Pause[9999]`: the artefacts exist, the member goes red and is named, and the capture is attached to the finding note.
- [ ] The licence-contention run reports its result **with its resolution**: if 0 of 30 stall, the note states that this bounds the per-invocation stall probability below **9.5 % at 95 % confidence** (1 − 0.05^(1/30)) and therefore does **not** exclude the observed rate. A bare "0/30, hypothesis unsupported" is not acceptable.
- [ ] `GOVERNANCE/VERIFICATION.md` carries a row stating either the cause or, plainly, that it remains unknown, what is now guaranteed instead, and **what would close it** — either a captured `sample` backtrace or a stated number of clean hook invocations.

**Outputs.** One commit. Finding note at `audit/AUDIT04_H_stall/FINDING.md` with
the 30-run table and any capture.

---

### H4 — The SIGSEGV: a measured rate and a mechanism candidate (M)

**Goal.** Replace an anecdotal rate with a measured one, test the mechanism the
crash reports point at, and decide whether the sentinel adjudication remains
sufficient.

**Owners.** `tests/MUnit/run-tests.sh` (the adjudication, lines 202–232),
`GOVERNANCE/VERIFICATION.md:157` (the claim).

**Dependencies.** H3.

**Evidence plan G does not have.** `~/Library/Logs/DiagnosticReports/` holds **25**
`WolframKernel` reports. **23 of 25** share one signature: SIGSEGV /
`EXC_BAD_ACCESS`, faulting **thread 10** — a pthread started from
`libWolframRTL_Kernel.dylib` — with the faulting frames in unnamed JIT or
compiled memory. **2 of 25** differ: thread 0, `mathlink` frames. The 2026-09-08
report shows a kernel that lived about three seconds (launch 12:44:15.35,
capture 12:44:18.42).

Two things follow, and both are for you to confirm or refute rather than assume.
The dominant fault is **not on the main thread and not in the shutdown path**,
which is what `VERIFICATION.md:157` asserts. And an asynchronous worker-thread
fault would explain all three puzzles at once — the crashing set differing every
run, each test being clean 3/3 standalone, and the per-run count varying between
0 and 5 — because it depends on thread scheduling rather than on test content.

**Steps.**

**H4.1 — establish the rate.** Run the full MUnit suite 10 times at a **fixed
SHA**, in the background, with `--quiet`, recording the environment. For each
run record the crash set, exit codes and sentinel presence. Report per-test crash
frequency **with a binomial interval**, and the run-level distribution **against
a Poisson expectation** — the discriminating question is whether crashes are
run-correlated (session or machine state) or test-correlated, and the observations
0-in-one-run and 5-in-one-run are hard to reconcile with a constant independent
per-test rate.

**H4.2 — test the mechanism.** Correlate the crash sets against the diagnostic
reports by timestamp, and report how many crashes carry the thread-10 RTL
signature and how many the `mathlink` one. If the split persists, **G2 is itself
two defects** and the ledger must say so. Record peak RSS per test only if the
signature evidence is inconclusive; the historical memory-pressure note is a
weaker lead than a backtrace.

**H4.3 — close the sentinel's remaining hole.** The adjudication proves that
every line **evaluated**, not that every artefact **landed durably**. A stream
held open and flushed at teardown is exactly what a teardown fault loses, and no
existing plant covers it. Plant a crash between an `OpenWrite` and its `Close`
and record whether the sentinel still adjudicates correctly.

**H4.4 — close the enforcement hole.** `results/tests/runall/Status.txt` line 1
reads `OK=72 FAIL=0 TOTAL=72 SCOPE=all` and line 2 lists the crashes, but the
gate reads line 1 only, so the crash count can drift with nothing going red.
"Recorded, not hidden" is true of the file and false of the enforcement. Bring
the crash count into a gate with a declared ceiling.

**H4.5 — settle whether the stall and the crash are one defect.** Compare any
`sample` backtrace captured in H3.3 against the thread-10 signature. Same frame
in the RTL worker pool means one defect with two outcomes; anything else means
two. **Until such a comparison exists, they are two**, because the mitigations do
not transfer: a watchdog fixes a hang and does nothing for a crash, and the
sentinel adjudicates a crash and cannot adjudicate a hang.

**Acceptance criteria.**
- [ ] 10 runs at a fixed SHA, with the crash set per run and the environment recorded.
- [ ] Per-test crash frequency reported with a binomial interval; run-level dispersion reported against a Poisson expectation; the run-correlated versus test-correlated question answered or explicitly left open with the reason.
- [ ] The diagnostic-report signature split is reported with its denominator, and the ledger states whether G2 is one defect or two.
- [ ] `VERIFICATION.md:157`'s "dies at shutdown" is either confirmed against the backtraces or corrected.
- [ ] An explicit statement of whether a pre-sentinel death was ever observed; if one is found, that is a **P0** and the suite's green is void until it is resolved.
- [ ] The buffered-write plant is executed and its result recorded.
- [ ] The crash count is read by a gate with a declared ceiling, verified by planting a count above it.

**Outputs.** One commit. Finding note at `audit/AUDIT04_H_segv/FINDING.md`.

---

### H5 — Coverage and mutation, carried forward with corrected criteria (L)

**Goal.** Unchanged from plan G Phases B and D: reduce the 22 modules at 0 %
coverage, then extend the mutation catalogue to what Phase B newly covers. Only
the acceptance criteria change.

**Dependencies.** H0 for the corrected mutation baseline. Phase B lands before
Phase D — mutants on uncovered code measure nothing.

**Carried unchanged from plan G:** the ranking rule (rank the 22 modules by
whether they carry a claim in a manuscript or a governance document, not
alphabetically); the requirement that every new test be verified by planting a
defect; floors compared strictly and floored to two decimals; never lower a floor
to accommodate new untested lines; the trap that `pytest` takes **no path
argument** here, because `pytest.ini` and the root `conftest.py` define the
collection set from the manifest.

**Corrected criteria.**
- [ ] **Coverage rises are attributed, not merely reported.** A table splits every point of the global rise into three named causes: a bite-verified new test, an arithmetic correction, or executed-but-unverified lines. Only the first may be quoted as progress. This exists because coverage has already moved 9.19 → 11.05 and 12.63 → 29.90 in this repository with no verification added.
- [ ] **The ratchet unit is decided before Phase B starts, not after.** This is author decision **H-D3**. Recommendation on the record: report the percentage, ratchet on **covered statement count**, which cannot fall merely because a new uncovered module landed.
- [ ] **The mutation catalogue gains a held-out arm.** Every newly covered module gets at least one semantic mutant with its prediction recorded before execution, as before — **and** a mechanically generated arm (every comparison operator flipped, every integer constant perturbed, across the owner set) whose kill rate is reported **separately**. The curated catalogue is written by the person who knows where the gaps are; `VERIFICATION.md` says so itself about the 25 → 30 growth, and one hundred per cent over an author-extended catalogue is not the same claim as one hundred per cent over a mechanical one.
- [ ] Both kill rates reported with their denominators and their staleness line from H0.2; no merged figure.

---

### H6 — Ledger, branch reconciliation and tag (M)

**Goal.** Close AUDIT04 with a record a reviewer can check, and reconcile the
branches from their measured geometry rather than from a stale statement.

**Dependencies.** H1–H5.

**Steps.**

**H6.1** — Reconcile `GOVERNANCE/VERIFICATION.md` end to end: every row names its
producer, its denominator and the SHA it was last measured at. Run
`tools/check_verification_numbers.py` and record the covered fraction — it was
12 of 44 at `af7690e` and every task above should raise it.

**H6.2 — branch reconciliation, corrected.** This is **not** master-plan task
T0.4: T0.4 is done, and tags `audit01-baseline` (`366d771`) and `audit01-closed`
(`6f56ea9`) already exist. The measured geometry is that `fixing` is 115 commits
ahead of and **7 behind** `main`, and `clean` is a strict ancestor of `fixing`.
**Inspect those 7 commits before doing anything**; a fast-forward as loosely
described in plan G would discard them. State what they contain, then merge in
the direction the content dictates.

**H6.3** — Tag the audit close. The message states the measured state — closure,
suite, manifest, coverage, both kill rates with their staleness line — **and what
remains open**, naming H3's stall if unresolved, H4's measured crash rate, and
`SUCCESSOR_PLAN_R4.md` Wave 0.

**H6.4** — Update `MEMORY.md`: the mutation pair, the branch geometry, the
comparator finding, the variant naming, and the plan lineage.

**Acceptance criteria.**
- [ ] Every `VERIFICATION.md` row carries producer, denominator and measurement SHA; the gate's covered fraction is stated and is higher than 12 of 44.
- [ ] The 7 commits on `main` are enumerated and their disposition stated before any merge.
- [ ] Tag message states the measured state **and** the open items, including the successor plan's Wave 0.
- [ ] `MEMORY.md` carries no superseded number.

---

## 6. Author decision register

Each halts its thread. Do not invent policy.

| ID | Decision | Options | Recommendation | Raised in |
|---|---|---|---|---|
| **H-D1** | The reading of the bio result, and whether `Contingency_Monitor`'s `gap` arm moves off the best-null comparator | (i) report all three comparators, draw no conclusion; (ii) adopt the median-null comparator as the headline and restate the result; (iii) keep the best-null headline with its knob-response declared beside it | **(i) now, (ii) or (iii) after H1.1's knob table is on the table** — the measurement should precede the reading | H1 |
| **H-D2** | What follows from both measures pricing a labelling | (i) keep both, publish the response profiles, claim nothing about wiring until a canonical-form code exists; (ii) commission a canonical-labelling wiring code as new work under the successor plan; (iii) withdraw the wiring claim | **(i) for AUDIT04, with (ii) routed to the successor plan** — decision #96 is not in question and is not reopened | H2 |
| **H-D3** | The coverage ratchet's unit | percentage / covered statement count / both | **report the percentage, ratchet on covered statement count** | H5 |

---

## 7. Format of the final report

One file: `audit/AUDIT04_H/REPORT.md`. It is the artefact I will review, and it
is judged against this skeleton. Prose in British English, no contractions.

1. **Verdict, in five sentences or fewer.** What is now known that was not, and
   what remains open. No preamble.
2. **What was measured.** One table: claim · command · denominator · result ·
   date · SHA. Every number in the rest of the report traces to a row here.
3. **Per task, H0 to H6.** For each: the goal in one sentence; what was done;
   the acceptance criteria as a checklist with each box either ticked with its
   evidence or left unticked **with the reason**; the plants performed and what
   they showed.
4. **Predictions and their outcomes.** Every pre-registered prediction, whether it
   held, and — where it did not — what that falsified. A plan whose every
   prediction held is a plan that predicted nothing.
5. **What contradicted this plan.** Any fact in §1 or §2 that measurement
   overturned, stated plainly. This section being empty is itself a claim and
   requires a sentence saying so.
6. **What was not done, and why.** Blocked tasks, author gates reached,
   deliberate exclusions.
7. **Open items, ranked**, each with the measurement that would close it.
8. **Commit trail.** One line per commit: SHA, task, one-sentence effect.

Three prohibitions on the report. No number without its denominator. No claim of
agreement or exactness without an elementwise symmetric difference. No conclusion
about biology in H1 — that is H-D1 and belongs to the author.

---

## 8. Execution order and effort

```
H0 (S) ──┬─→ H1 (M) ──┐
         ├─→ H2 (M/L) ─┼─→ H6 (M)
         └─→ H3 (M) ──→ H4 (M) ─┤
                       H5 (L) ──┘
```

H1 and H2 are independent of each other and of H3/H4, and are the scientific
core — do them first and in that order if working serially. H3 gates H4 because
every full-suite run needs a hook that terminates. H5 is the largest and the
least urgent. H6 closes.

| task | effort | gate |
|---|---|---|
| H0 record correction | S | — |
| H1 comparators | M | H-D1 at the end, not the start |
| H2 measures | M/L | H-D2 at the end, not the start |
| H3 stall | M | — |
| H4 SIGSEGV | M | — |
| H5 coverage and mutation | L | H-D3 **before** starting |
| H6 ledger and tag | M | — |

---

## 9. Verification block — run before every push

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
venv/bin/python tools/check_verification_numbers.py
venv/bin/python tools/snapshot_paper_numbers.py --check

# Wolfram tier — the pre-push hook is the ONLY thing that runs it (~40 min).
# CI cannot: hosted runners have no kernel.
make ci-local
```

**Wolfram kernel invocation, confirmed working:**

```bash
HOME=/Users/alberto /Applications/Wolfram.app/Contents/MacOS/WolframKernel -script <absolute-path>
```

The flag is `-script`, not `-noprompt -script` and not `-file`; the `HOME=`
prefix is required. `$ScriptCommandLine` is empty under `-script` — pass
arguments through the environment.

---

## 10. What must not happen

Stated as anti-goals, because each is a plausible misreading of this plan.

- **The simplicity claim is not reinstated.** H1 publishes comparators; it does
  not conclude. A report that ends "biological networks are simple after all" has
  failed this plan as surely as one that keeps the current overstatement.
- **No third complexity measure is created.** H2 measures the two that exist. The
  hybrid ban stands and is not the subject of H-D2.
- **No file is created where an owner exists.** Six of the seven tasks are
  enrichments of a named file. A new script is evidence that step one was skipped.
- **The 231 × 1000 null run is not repeated in full.** H1.2 needs no
  recomputation, and H1.1 needs a stated subsample. A full re-run burns hours and
  answers nothing this plan asks.
- **No acceptance criterion is ticked by a run over a denominator chosen after
  seeing the result.** That is the failure this repository has recorded six
  times, and every one of them was a guard reporting success over a set that
  excluded the defect.
