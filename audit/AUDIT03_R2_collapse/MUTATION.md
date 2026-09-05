# Mutation testing — does green mean anything?

**Measured against commit `5b51a46`** (the worktree the harness checked out;
later commits on `fixing` are not in the measurement).
**Harness:** `audit/AUDIT03_R2_collapse/mutation_harness.py`.
**Status of this file:** predictions registered **2026-09-04, before the run
finished**. Results are appended below, not written over the predictions.

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

*Appended when the run completes: kill rate per owner with its denominator,
every survivor adjudicated as gap or equivalent, and every owner with zero kills
named explicitly.*
