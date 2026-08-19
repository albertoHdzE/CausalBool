# Bitácora 07 — Datasaurus audit of everything built so far

**Date:** 2026-08-18
**Trigger:** the assessor put Phase 2 down to Datasaurus syndrome. It was right,
and the obvious next question was whether the disease was confined to Phase 2.
**Instrument:** the four gates of the `datasaurus` skill (G1 render / G2 common
coordinate / G3 knobs / G4 mechanism), promoted to a global skill for this
audit.
**Result:** three infected sites, three clean. Two conclusions survive on other
evidence; one claim is withdrawn.

---

## 0. Why the audit used someone else's checklist

A mature `datasaurus` skill already existed in the `deconv-lab` programme: four
enforced gates, a seven-case ledger, ten catalogued forms, and — the detail that
decided it — it had itself been rewritten *after failing while being followed*.
Writing a fresh checklist here would have meant auditing with an instrument built
from my own intuition, which is exactly how the infection got in. The skill was
promoted to `~/.claude/skills/datasaurus/` and this project's cases added to its
ledger.

My two known failures map onto its gates without adjustment:

| failure | gate |
| --- | --- |
| Phase 2 reported with no figure at all | **G1**, and its tell *"you can quote the number but have not drawn the shape"* |
| C22 compared BDM at 17 against 23 edges | **G2**, *"put both objects in a common coordinate first"* |
| never asked what BDM is for a random matrix at that density | **G4**, *"what would this number be under a process known to contain nothing?"* |

---

## 1. INFECTED — C22, the structure axis. **Withdrawn.**

**Claimed.** "On the structure axis, where both matrices are 14 × 14 and size
cannot confound, the gate network's connectivity is *more complex* (BDM 156.45
against 123.37) and denser (23 edges against 17)."

**The gate it failed.** G2. I matched *shape* and congratulated myself on it in
the same sentence in which I reported the density difference. Density is a
nuisance dimension BDM responds to, and it was not matched.

**Measured.** Random 14 × 14 matrices give BDM 189.39 ± 22.75 at 17 edges and
214.83 ± 17.40 at 23. Expected difference from density alone: **+21.82 bits**
against the +33.08 reported. **Density explains 66 per cent of the claim.**

**What is true instead, and it is more interesting.** Both networks sit far
*below* random at their own density — gate 156.45 against 214.83 (z = −3.35), CPT
123.37 against 189.39 (z = −2.90). **Both connectivity structures are about three
standard deviations more compressible than random, and they are not
distinguishable from each other on that axis.** The original claim inverted the
interesting fact and attributed to complexity what was edge count.

## 2. INFECTED — C19, the model term. **Number compromised, conclusion survives.**

**Claimed.** Algorithmic two-part length, gate network 933.0 bits against CPT
904.5, a margin of +28.5.

**The gate it failed.** G2 again, and I did not see it even while writing the
protocol clause about it. The two model terms are BDM of arrays of **different
size**: the gate's truth tables are 14 × 8 = 112 cells, the CPT's quantised
parameters 14 × 32 = 448. BDM grows with cell count. The terms were never
comparable.

**Measured.** Against each object's own null at matched shape *and* density:
gate tables −29.94 bits, CPT parameters −485.84. But that repair is itself
encoding-dependent — a 4-bit quantisation of probabilities produces repeating
low-order bit patterns that compress for reasons that have nothing to do with the
model. So the honest verdict is not "the sign reverses" but **"BDM applied to two
representations I chose cannot settle this"**.

**What survives.** The *counting* comparison, +51.1 bits, does not involve BDM at
all and is untouched. It gives the same sign on all three binarisations. **C19's
conclusion — the table describes the panel more compactly — stands on the
counting evidence alone**, and the algorithmic figure is demoted to
"instrument-dependent, not decisive". The direction of the size error also
happened to run against the CPT, so the verdict was conservative.

## 3. INFECTED — a G1b gap across Gate 1.0 and Phase 1b

Every null in this package before notebook 03 was reported as `mean ± sd` and
never drawn. That is the same omission that hid the Phase 2 overfitting penalty
for a week. It did not, in the event, hide anything else (see §4), but it was
luck rather than method: no figure existed that could have shown it.

## 4. CLEAN — C5–C10, Gate 1.0

The obvious worry was that Phase 2's hidden overfitting penalty had propagated
backwards. It has not, and the reason is structural rather than fortunate: Gate
1.0's statistics are **in-sample**, with no train/test split, so there is no
overfitting penalty for a null to absorb. Measured: base rate 0.6642, self-block
null mean **0.6645**, a difference of +0.0002. The null sits exactly where it
should. G4 was satisfied throughout — rule 110, random, and persistent-random
controls, with the permutation null caught and replaced.

## 5. CLEAN — C1–C4, reference parity

Immune by construction, and this is worth stating because it is the shape a
Datasaurus-proof claim has. Parity was asserted as **elementwise equality of
3,124 individual numbers**, not as agreement of any summary. G2 is satisfied in
its strongest form: the objects were compared member by member, and the ledger
reports the comparison, not a percentage.

## 6. CLEAN — C20, no named gates

"0 of 14 nodes named" is a count of an elementwise property — which nodes the
family could name — not a summary over a distribution. There is no shape for it
to hide. It is also the entry that most resembles what the skill asks for:
a claim about objects, reported as objects.

---

## 7. What this changes in the ledger

| entry | status after audit |
| --- | --- |
| C22 | **WITHDRAWN** and replaced: both networks ≈3σ more structured than random at their own density, not distinguishable from each other |
| C19 | number **demoted** to instrument-dependent; conclusion stands on the counting comparison |
| C5–C10, C1–C4, C20, C21, C23–C28 | unchanged |

No headline conclusion of the project changes. B4 is still refuted, B6 is still
unsupported, Gate 1.0 still explains GWP3's result. What changes is that two
numbers I had used as *supporting* evidence turn out to have been measuring
density and array size.

## 8. The pattern in my own failures

Six control-caught errors and now three audit-caught ones. Sorting them:

- **Mechanical faults** — a leaky decoder, an unexecuted notebook, widget outputs,
  a runtime in a content hash. My checks catch these reliably.
- **Interpretive faults** — a mean that sums an effect with a penalty, a BDM
  compared across densities, a BDM compared across array sizes. My checks caught
  **none** of these. Every one was found by an outside challenge or by a
  deliberate audit.

The common shape is that I match on the dimension I have thought of and never
enumerate the dimensions the statistic actually responds to. That is now the
first line of G2 in the global skill, and the standing rule taken from it is:
**no phase gets a verdict before it gets a figure, and no statistic gets
subtracted before its null's location is explained.**

## 9. Next

Step 3: Phase 3, at daily frequency, which was pre-declared to run regardless of
the Phase 1 and Phase 2 outcomes and now begins with the audit's rule in force.
