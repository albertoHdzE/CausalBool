# Mutation testing — does green mean anything?

**Predictions registered against `5b51a46`; results measured against `c9bc412`**
— the run was restarted after a reboot, and the discrepancy is declared in the
Results section rather than reconciled.
**Harness:** `audit/AUDIT03_R2_collapse/mutation_harness.py` (`--report`).
**Status of this file:** predictions registered **2026-09-04, before the run
finished**. Results appended **2026-09-05**, not written over the predictions.

> **Headline: semantic kill rate `23/25` = 92.0 %. Unit-test kill rate
> `19/25` = 76.0 %.** Two owners have zero unit-test kills and one is not
> measured at all. The gap between those two rates is the point of this file.

---

## Why predictions are written down first

A surviving mutant is either a **coverage gap** or an **equivalent mutant** that
changes nothing observable. The two are opposite findings — one is a hole in the
suite, the other is a fact about the code — and the standard failure of mutation
testing is to look at a survivor *after the fact* and reason one's way to
"equivalent". That reasoning is unfalsifiable once the answer is known.

So the predictions below are committed before the rate is known. Where I am
wrong, the record shows it.

---

## The catalogue is not homogeneous, and the rate must not pretend it is

28 mutants across 9 owners, but they are not all the same kind of evidence:

| kind | count | what a kill proves |
|---|---|---|
| **semantic** — an inverted comparison, an off-by-one, a dropped branch | 25 | the suite checks the *answer*. This is the evidence that matters. |
| **reachability probe** — a public function renamed away | 3 | only that *something imports it*. A kill here is nearly free and proves almost nothing about assertion quality. |

The three probes are `py-dl-schema` (`schema_normal_form_length`),
`py-dnf-minimal` (`minimal_dnf`) and `py-essential-vars`
(`essential_variables`). **They are reported separately and excluded from the
headline rate**, because folding trivially-killable mutants into a score is how
a mutation number gets inflated. Their real use is the opposite one: a probe
that *survives* means the owner is unreachable — dead code wearing a public
name.

---

## Registered predictions

### Predicted killed, high confidence — 21 semantic mutants

The eleven `Gates` mutants each change a truth table that per-gate tests in
`tests/MUnit/Analysis/` assert directly. The first five were already observed
killed by 14, 12, 12, 7 and 8 tests respectively before these predictions were
written, so this is partly observation rather than prophecy.

`phi-no-reverse` drops the LSB/MSB bit-reversal, which is load-bearing in every
repertoire; `core-composed-y5` collapses the composed 6-node update onto the
synchronous one and was **measured in AUDIT03 to differ on exactly 32 of 64
rows**, so the 135/135 cross-language parity gate should refuse; `dl-drop-indegree`
removes the field that makes `D_formula` decodable and should break the Kraft
test and the Wolfram↔Python parity gate together.

### Predicted killed, moderate confidence — 4

- **`dl-binomial-off`** and **`cformula-kofn`** shift a description length by a
  small amount. Nothing in the MUnit suite pins an exact `D` for an arbitrary
  network; the kill, if it comes, should come from
  `tools/test_description_length_parity.py`, which executes the Wolfram producer
  and compares it to the Python owner. **If these survive, the finding is that
  no test pins an absolute description length — only relative agreement.**
- **`core-alloffsets`** halves the offset family. Killed only if the parity
  corpus contains a network with more than one free coordinate.
- **`core-applygate-default`** makes the companion-code `NOT` the identity.
  Killed only if the 135 parity cases include a `NOT` node — which I have not
  checked, and deliberately have not, so the prediction stays honest.

### Predicted to SURVIVE as a genuine coverage gap — 1

**`py-paths-root`**: `repo_root` matches an ancestor holding `src/` **and**
`results/`; the mutant loosens it to **or**.

This is a real behavioural change, and I can name the input that exposes it:

```
tests/          contains results/ but NOT src/
```

so `repo_root(<anything under tests/>)` returns the repository root under `and`
and returns **`tests/`** under `or`. Every consumer would then build paths one
level too deep.

**The suite will not catch it**, because I wrote those tests and they only pass
start paths under `src/` and `tools/` — neither of which holds either marker —
and the default start is the module itself. `test_repo_root_is_depth_independent`
parametrises over depth, which is the property the four collapsed copies lacked,
but never over an ancestor carrying **one** marker.

**This is a coverage gap, not an equivalent mutant, and it is mine.** If it
survives, the fix is a test case starting under `tests/`.

### Prediction I am least sure of — 1

**`io-drop-logic`** rewrites the string `"logic"` to `"gates"` in
`src/scripts/NetworkIO.m`. `apply_mutant` replaces **every** occurrence, so if
`"logic"` appears in more than one role the mutant is broader than its
description. A kill would then be real but would not isolate the AUDIT02/H
defect it is named for. Worth re-running as a single-occurrence patch if it
matters.

---

## Results

**Run completed 2026-09-05, `28/28` scored, `complete=true`.**
Regenerate every number below with:

```
venv/bin/python audit/AUDIT03_R2_collapse/mutation_harness.py --report
```

That reporter is part of the harness, not a second script, and it **refuses**
on an absent results file, an empty mutant list, or a run marked
`complete=false` — a partial file must never be quotable as a final rate. All
three refusals were verified by planting them.

### A commit discrepancy, declared rather than reconciled

**The predictions above were registered against `5b51a46`. This run measured
`c9bc412`.** The reboot that destroyed the first attempt also forced the
re-run onto a later commit. The intervening commits did not touch any mutated
owner, but the predictions were not written against this exact tree and the
record should say so rather than quietly align the two.

### The rate, with its denominator

| rate | value | what it means |
|---|---|---|
| **semantic** | **23/25 = 92.0 %** | the headline: mutants that change an answer |
| **unit-test** | **19/25 = 76.0 %** | of those, how many an MUnit or pytest test caught |
| probes | 3/3 | excluded; a kill proves only that something imports the owner |

**The 16-point gap between those two rows is the finding of this exercise.**
Four semantic mutants were killed *only* by a governance gate (`closure:wolfram`),
with no MUnit and no pytest test detecting them. A kill by a closure gate means
the programme notices; it does not mean the suite checks the answer. Those are
different claims and a single 92 % would have merged them.

### Per owner

| owner | killed | semantic | unit-killed | verdict |
|---|---|---|---|---|
| `Gates` | 11/11 | 11 | **11/11** | the strongest layer in the repository |
| `description_lengths` | 5/5 | 4 | 4/4 | |
| `IndexAlgebra` | 1/1 | 1 | 1/1 | |
| `BioMetrics` | 2/3 | 3 | 2/3 | one survivor |
| `causalbool_paths` | 2/2 | 2 | 1/2 | |
| `CausalBoolCore` | 3/3 | 3 | **0/3** | **zero unit-test kills** |
| `NetworkIO` | 0/1 | 1 | **0/1** | **zero kills of any kind** |
| `deconvolution` | 2/2 | **0** | — | **not measured: probes only** |

Three owners need naming explicitly, as the plan requires:

**`NetworkIO` — zero kills of any kind.** Its single mutant survived everything.

**`CausalBoolCore` — zero unit-test kills.** All three of its mutants were caught
solely by the cross-language parity gate. This is the standalone companion core,
whose self-containment is a *declared exception* in `GOVERNANCE/CORE.md` and
whose stated justification is precisely that parity keeps it honest rather than
shared code. **So the exception is holding exactly as declared** — but nothing
else is watching it, and if the parity gate were ever skipped the owner would be
undefended. That is the cost of the exception, now measured rather than assumed.

**`deconvolution` — not measured.** Both its mutants are reachability probes, so
its semantic denominator is zero. `minimal_dnf` and `essential_variables` are
declared owners in `CORE.md` and **no mutant has ever tested whether the suite
checks their answers.** The reporter prints `NOT MEASURED` rather than `0/0`,
because a zero denominator reading as a clean sheet is the vacuous pass this
programme keeps removing. Phase 4 must add semantic mutants here first.

### Survivors, adjudicated

Both are **coverage gaps**. Neither is an equivalent mutant, and in both cases
that is decidable without appeal to intuition, because each mutant reproduces a
defect this programme has already measured in the wild.

**`io-drop-logic` — coverage gap, and the most consequential result here.**
The mutant makes the corpus loader read the classification **label** instead of
the authoritative `logic` formula. It is not equivalent: it changes what is
loaded for the entire corpus.

Its significance is that **a second instrument, built for a different purpose,
independently found the same defect this week.** The AUDIT04 Phase 5 diagnostic
established that reading the label as a statement about evaluability is exactly
why **1,943 of 3,977** corpus nodes were recorded as having no derivable truth
table when they have one. Phase 5 showed the defect had happened; the mutation
run adds what Phase 5 could not — **nothing in the suite would catch it being
reintroduced.**

`CORE.md` already records that two of the five collapsed `LoadJSONNetwork`
copies carried this defect. The owner was fixed; the *test* that would keep it
fixed was never written.

**`cformula-kofn` — coverage gap.** The mutant reverts the `KOFN` branch of
`C_formula` to the drifted `1+d` form found in two copies during the AUDIT03
collapse. It produces a different number, so it is observable in principle.

The pre-registered prediction paired it with `dl-binomial-off` and named the
finding in advance: *if these survive, nothing pins an absolute description
length, only relative Wolfram↔Python agreement.* **The pair split** —
`dl-binomial-off` was killed, `cformula-kofn` survived — which is a sharper
result than either outcome alone: the gap is not general to description length,
it is specific to the `KOFN` branch.

### Predictions, scored honestly

| prediction | outcome |
|---|---|
| 21 semantic mutants killed, high confidence | **held** |
| `dl-binomial-off`, `core-alloffsets`, `core-applygate-default` killed, moderate | **held** — all three killed |
| `cformula-kofn` may survive, with its finding named | **held** |
| **`py-paths-root` will SURVIVE as a coverage gap** | **FAILED — it was killed** |

**The failed prediction, and why the substance of it still stands.**
`py-paths-root` was killed by `closure:wolfram` and by **nothing else** — zero
pytest kills. The prediction claimed the unit tests would not catch it, and
*that claim was correct*: `test_repo_root_is_depth_independent` still never
parametrises over an ancestor carrying exactly one marker, and the gap in tests
I wrote is still there. What the prediction got wrong is the outcome, because I
did not account for a governance gate counting as a kill.

Recording it as "held" would be the exact after-the-fact reasoning this file
exists to prevent. **It is scored as failed**, and the underlying coverage gap
is carried into Phase 3 regardless of the kill, because a mutant killed only by
a closure gate is not a tested mutant.

---

## AUDIT04 Phase A — predictions for the five new `deconvolution` mutants

**Registered 2026-09-05, before any of them was run.** The owner previously had
a semantic denominator of **zero** — both its mutants were reachability probes,
so `minimal_dnf` and `essential_variables` were declared owners whose assertion
quality had never been measured. These five give it a denominator.

The existing evidence is 23 tests in `index-deconvolution/tests/test_deconvolution.py`.
I have deliberately **not** read their fixtures before writing the predictions
below, because knowing which essential sets they use is exactly what would make
prediction 5 unfalsifiable.

| mutant | change | prediction |
|---|---|---|
| `dec-essential-invert` | `!=` → `==` in the sensitivity test | **KILLED**, high confidence |
| `dec-essential-top` | `range(n)` → `range(n - 1)` | **KILLED**, high confidence |
| `dec-dnf-offset` | `v == 1` → `v == 0` when collecting minterms | **KILLED**, high confidence |
| `dec-dnf-polarity` | activators ↔ inhibitors | **KILLED**, *moderate* |
| `dec-reduce-index` | `1 << j` → `1 << e` in `reduce_column` | **SURVIVES**, with its input named |

**High confidence (1–3).** `test_essential_variables_equal_connectivity` and
`test_disconnected_node_is_never_sensitive` assert the essential set directly, so
inverting sensitivity returns its complement and must fail. Dropping the
highest-indexed variable breaks any exact-recovery test whose network depends on
it. Covering the off-set inverts every clause, and
`test_regulatory_dnf_identification_and_reproduction` asserts reproduction.

**Moderate (4).** Swapping activators and inhibitors is only observable through a
clause carrying **both**. If the DNF tests use activator-only clauses — which is
the common shape for regulatory logic — it survives.

**Predicted to SURVIVE (5), with the failing input named in advance.**
`reduce_column` maps original bit `e` to reduced index `j`. The mutant writes to
`1 << e` instead of `1 << j`, so the two agree **exactly when `j == e` for every
essential variable** — that is, whenever the essential set is contiguous from
zero (`[0]`, `[0,1]`, `[0,1,2]`). It differs only on a non-contiguous set such as
`essential = [0, 2]`, where the reduced table must be indexed by `1` and the
mutant indexes by `2`, writing out of the intended slot.

Small hand-built test networks almost always have contiguous essential sets. If
it survives, the finding is that **`reduce_column` is never exercised on a
non-contiguous essential set**, and the fix is a test with a genuine hole in the
support — not a claim that the mutant is equivalent, because it is not.

### Result — `deconvolution` goes from NOT MEASURED to 5/5

Measured 2026-09-05 against the owner's own suite
(`index-deconvolution/tests/`, 23 tests). These are **targeted** runs, not full
harness runs: a kill by a subset of the suite is still a kill, but the
per-instrument attribution comes from the full run at the close of Phase A.

| mutant | predicted | actual | killed by |
|---|---|---|---|
| `dec-essential-invert` | KILLED | **KILLED** | 8 tests |
| `dec-essential-top` | KILLED | **KILLED** | 6 tests |
| `dec-dnf-offset` | KILLED | **KILLED** | 2 tests |
| `dec-dnf-polarity` | KILLED (moderate) | **KILLED** | 1 test |
| `dec-reduce-index` | **SURVIVES** | **KILLED** | 6 tests |

**Four predictions held. The fifth failed, and the reason is the useful part.**

I predicted `dec-reduce-index` would survive because it is inert whenever the
essential set is contiguous from zero, and I assumed the fixtures would be small
hand-built networks with sets like `[0, 1]`. They are not. It was killed by:

```
test_exact_recovery_random_symmetric
test_exact_recovery_random_full
test_biological_networks_exact_recovery
test_reachable_state_correlation_can_hide_inputs
test_verify_forward_is_independent_and_exact
test_connectivity_recovered_exactly
```

**Random and biological networks have holes in their support; hand-built ones do
not.** The suite is stronger than I predicted precisely because it does not rely
on hand-built cases. That is a property worth naming, because the obvious way to
write a fixture — construct a small network by hand — would have left this exact
mutant alive and the gap invisible.

`dec-dnf-polarity`, the one I was least sure of, was killed by a single test.
One test is a thin margin: deleting
`test_regulatory_dnf_identification_and_reproduction` would leave clause polarity
entirely unchecked. Recorded here rather than fixed, since the owner now has a
denominator and Phase D is where thin margins are widened.

**No new tests were required for this owner.** The gap was in the *catalogue*,
not in the suite: the tests existed and were good, and nothing had ever asked
them a semantic question.

---

### What this hands to Phase 3

Test targets are now chosen from evidence rather than from file size. In order:

1. `NetworkIO` — a test that fails when the loader reads the label (the only
   zero-kill owner, and the defect is already documented twice).
2. `deconvolution` — semantic mutants first, since its assertion quality is
   currently unmeasured, then tests to kill them.
3. `CausalBoolCore` — unit tests that do not depend on the parity gate running.
4. `causalbool_paths` — the `py-paths-root` case: a start path under `tests/`.
5. `BioMetrics` — a test pinning an **absolute** `C_formula` for `KOFN`.


---

## Run 2 — `f2c2f77`, 2026-09-05. Every hole closed.

    KILL RATE: 33/33
    SEMANTIC   30/30 = 100.0%      (was 23/25 = 92.0% at c9bc412)
    UNIT-TEST  30/30 = 100.0%      (was 19/25 = 76.0%)
    probes      3/3, excluded from both rates

    BioMetrics 3/3 · CausalBoolCore 3/3 · Gates 11/11 · IndexAlgebra 1/1
    NetworkIO 1/1 · causalbool_paths 2/2 · deconvolution 7/7 (5 semantic)
    description_lengths 5/5 (4 semantic)

### The denominator moved, and that must be said before the rate is

The catalogue went 25 semantic -> 30 because Phase A **added five**, for
`deconvolution`, which had none. A rate scored over a catalogue extended by the
person who knew where the gaps were is not comparable to the one before it. The
honest, like-for-like statement is:

    on the ORIGINAL 25 semantic mutants, the unit-test rate moved 19/25 -> 25/25

and the five new `deconvolution` mutants were killed on their first run.

### What closed each of the three named owners

| owner | before | what closed it |
|---|---|---|
| `NetworkIO` | zero kills of any kind | `TSK-ARCH-005-NetworkIOContract.m` — 8 hermetic assertions on `LoadJSONNetwork`, fixture built in-test so it asserts the loader's contract rather than the corpus contents |
| `CausalBoolCore` | 3/3 by the parity gate, 0 by unit test | `TSK-ARCH-006-CausalBoolCoreContract.m` — needs no Python side, so the owner is defended even if parity is skipped or refuses |
| `deconvolution` | **NOT MEASURED** (probes only) | 5 semantic mutants written first, then the tests; 5/5 killed |
| `BioMetrics` (survivor) | `cformula-kofn` alive | `TSK-BIO-METRICS-002-AbsoluteKOFN.m` — pins an **absolute** description length; the d=1 blind spot documented in the suite |
| `causalbool_paths` (survivor) | killed by `closure:wolfram` only | 7 tests in `test_causalbool_paths.py`; 0 -> 3 pytest kills |

### Predictions, scored

One registered prediction FAILED. `dec-reduce-index` was predicted to SURVIVE on
the reasoning that it is inert whenever the essential set is contiguous from
zero, and that fixtures would be small hand-built networks. It was KILLED by
`test_exact_recovery_random_symmetric`, `test_exact_recovery_random_full` and
`test_biological_networks_exact_recovery`, among others. Random and biological
networks have holes in their support; hand-built ones do not. **The obvious way
to write that fixture would have left the mutant alive and the gap invisible.**

### What 100% does not mean

That the code is correct, or that the suite would catch a defect nobody thought
to write as a mutant. It means every defect **in this catalogue** is caught by a
test rather than by a gate. The catalogue is the measure: 33 mutants, 8 owners.
Phase D extends it to the newly covered modules, and the parser contract tests
already show why that matters — three of four do not catch a planted defect.
