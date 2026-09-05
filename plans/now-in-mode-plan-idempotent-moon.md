# AUDIT03-B — surgical cleaning after the core collapse

## Context

The previous phase (items 1–8, commits `651aaa7` … `2e6f1ba`) is **complete**.
It established one owner per concept (`GOVERNANCE/CORE.md`), installed the
`monolithic-code` law, declared test membership in `tests/MUnit/MANIFEST.tsv`,
and took the suite from `OK=54 FAIL=1 TOTAL=55` to **`OK=65 FAIL=0 TOTAL=65`**.

That work also produced an honest list of what it did **not** clean, and this
phase closes the tractable part of that list. Two author decisions taken
2026-09-04 scope it:

- **Quarantine:** paper-facing first, the rest reclassified honestly. No fake
  promotions.
- **Paper coverage:** measure and enumerate only. No producer wiring this pass.

### The finding that reorders the phase

`src/Packages/Integration/SelfTest.m` is **a fourth engine**. It carries private
reimplementations of the gate semantics — `myAnd`, `myOr`, `myXor`,
`allPosibleInputsReverse`, `runNetwork` — never checked against
`Integration`Gates`ApplyGate`. It is advertised in `README.md:68` as one of the
**core packages**, and `SelfTestRun` is invoked by nothing. Its only caller,
`tests/SelfTest.m`, lives outside `tests/MUnit`, so it is not in the manifest,
is not run by the suite, and exports `{"OK", DateString[]}` **unconditionally**.

Both censuses missed it: the AST arm is Python-only, and the Wolfram arm matches
normalised text, so single-line definitions under *different names* are
invisible to it. This is the fourth time a guard or a body-fragment search has
beaten a hash-based census in this audit, and it is the strongest remaining
argument for the `monolithic-code` pre-flight.

---

## The pass, in execution order

### 1. The fourth engine — `SelfTest.m`

**Measure before touching.** Run `myAnd`/`myOr`/`myXor` and `runNetwork` against
`Integration`Gates`ApplyGate` and `Integration`Experiments`CreateRepertoiresDispatch`
elementwise, over every arity 1..6 and every connected subset — the same shape as
`audit/AUDIT03_R2_collapse/probe_alloffsets_parity.wl`. Print the denominator.

Then adjudicate on the evidence, not in advance:

- **agree everywhere** → drift. Delegate to the owner, keep `SelfTestRun` as a
  thin smoke check, archive nothing silently.
- **disagree anywhere** → **stop**, report which cells and why, and do not
  collapse. Two concepts need two names (the `composedUpdate6Node` precedent,
  where 32 of 64 rows differed *correctly*).

`allPosibleInputsReverse` is additionally duplicated with `src/integration/Alpha.m`
and carries a typo in its name; resolve it under the same rule.

Correct `README.md:68`, which advertises `SelfTest.m` as a core package that
nothing runs. Add `tests/SelfTest.m` to the manifest with its true kind — it
exports a literal status, so it is `quarantine` until it has a predicate, or
`test` once step 2's pattern is applied to it.

**Guard:** extend `tools/check_single_engine.sh` with the gate-semantics body
signature (`Count[list, 0] == 0` / `Mod[Total[list], 2]`), so a fifth private
copy of AND/OR/XOR cannot appear silently. Verify by planting a copy.

### 2. `VerificationSamples.m` — a real predicate, then promotion

Measured: of the eleven quarantined files, **this is the only one whose output is
referenced by an active manuscript** (`papers/method/manuscript_formal/method_paper.tex`;
the other ten appear only in `doc/newIntPaper/` and `doc/finalpaper/`, which
`CLAUDE.md` declares provenance archives).

It computes truth tables for **XOR/XNOR, KOFN k=2, CANALISING case A and
IMPLIES** and exports them as "samples" **without checking a single row**. These
are the most load-bearing objects in the programme.

Add the predicate that was always available: compare every sampled row against
the closed form stated independently of `Gates.m` —
`XOR = Mod[Total, 2]`, `XNOR = 1 - Mod[Total, 2]`,
`KOFN = Boole[Count[·,1] >= k]`, `IMPLIES = Boole[a == 0 || b == 1]`,
`CANALISING` per `GOVERNANCE/GLOSSARY.md` (the non-canalised branch is `Or`, not
a constant). Export `If[allOK, "OK", "FAIL"]`, promote to `test` in the manifest.

**Negative control, run and observed:** perturb one truth-table row and confirm
the file goes red. A predicate that has not been seen to fail is decoration.

### 3. The other ten — honest reclassification, not promotion

They are artefact producers for the historical archives. Reclassify each in
`MANIFEST.tsv` as `producer` with the *measured* reason — which `doc/` file
consumes it — rather than leaving them under a quarantine label that implies
they are tests awaiting repair. Nothing is promoted, nothing is deleted, and the
manifest stops overstating the tree.

### 4. Two files invoked by nothing at all

`tests/MUnit/Algo/TSK-ALGO-PerfTable.m` and
`tests/MUnit/Compare/TSK-COMPARE-CHARTS.m` export no status and are referenced by
**no** script, Makefile target or gate. Confirm with a second search on a body
fragment, then move to `archive/` per repository policy — preserved, not deleted.

### 5. `verify-paper` — enumerate the coverage honestly

`papers/method/artifact_baseline/artefacts.json` declares **7 covered, 1
pending**, but the pending entry is a catch-all — *"remaining appendix/expansion
tables"* — with no enumeration, while the two active manuscripts carry **34
`tabular` environments** (21 formal, 13 computational). The gate's output reads
like `7/8` and is not.

Replace the catch-all with a per-table inventory: every number-bearing table in
both active manuscripts, listed `COVERED` (naming its producer) or `UNCOVERED`
(with the reason). Report the honest fraction in the gate's summary line. This
is **measurement, not wiring** — no producer is built this pass, and the
resulting number is expected to be materially worse than `7/8`, which is the
point.

### 6. Orphans — adjudicated, not deleted on a grep

29 Python (18 in active paths) and 4 Wolfram, from
`audit/AUDIT03_R2_collapse/orphan_census.py`. Label each **dead** / **public API**
/ **capability awaiting use**, with evidence. Delete only where dead is proven;
record the rest.

Two are already understood and go in the ledger rather than the bin:

- `posterior_probabilities` (`imp-prices/.../belief_network.py`) — the module
  scores hard argmax labels, so calibrated posteriors are unused. **A capability
  the protocol has not yet called for**, not a defect; it means no calibration
  claim has been made.
- `compute_d_bdm_correlation`, `generate_bio_repertoires`
  (`src/integration/bio_D_experiment.py`) — inspect against the description-length
  owner before judging; that file is named in `GOVERNANCE/CORE.md`'s neighbourhood.

State again, in the output, that the census **under-reports**: it over-counts
references by design, so the printed set is a floor.

### 7. Two small, real defects

- **`src/data/` has no `__init__.py`**, so `src/analysis/Cancer_Corruption.py`
  cannot be imported at all (verified pre-existing against the unmodified file
  via `git show`). Fix, then confirm the module imports.
- **`D_formula` IMPLIES/NIMPLIES** — the `log2(d(d-1))` field prices an ordered
  pair the engine cannot choose (the caller always sorts, so the antecedent is
  always the lower index). Measured: the cost difference is **0.00000 bits**
  everywhere (`log2 2 = 1`, identical to the default branch) and the corpus has
  **zero** IMPLIES/NIMPLIES nodes, so no published number moves. Add the comment
  and a `d == 2` assertion so a `d=3` node fails loudly instead of paying a
  phantom field. **No formula change.**

### 8. Ledger and guards

Declare every delta in `tests/MUnit/BASELINE.md` with its cause. Update
`GOVERNANCE/CORE.md` (any new owner, any new exception), `MANIFEST.tsv`, and
`audit/AUDIT03_R2_collapse/DUPLICATION.md`. Add step 1's guard and step 5's
coverage line to `make closure`.

---

## Critical files

- `src/Packages/Integration/SelfTest.m`, `tests/SelfTest.m`, `README.md:68` — the
  fourth engine.
- `src/Packages/Integration/Gates.m` — the owner it must be measured against.
- `tests/MUnit/Sampling/VerificationSamples.m` — the predicate.
- `tests/MUnit/MANIFEST.tsv`, `tools/check_test_manifest.sh` — reclassification.
- `papers/method/artifact_baseline/artefacts.json`, `tools/verify_paper_artefacts.py`
  — coverage enumeration.
- `audit/AUDIT03_R2_collapse/orphan_census.py` — reuse; do not rewrite.
- `tools/check_single_engine.sh` — one added signature.
- `src/data/__init__.py`, `src/Packages/Integration/BioMetrics.m`,
  `src/description_lengths.py` — step 7.

Reuse, do not reimplement: `probe_alloffsets_parity.wl` (parity shape),
`duplication_census.py`, `orphan_census.py`, `test_efficacy_census.py`.

## Verification

```bash
# 1. the fourth engine — parity BEFORE any collapse, denominator printed
HOME=$HOME .../WolframKernel -script audit/AUDIT03_R2_collapse/probe_selftest_parity.wl
zsh tools/check_single_engine.sh                 # new gate-semantics signature listed

# 2. the predicate must be SEEN to fail
zsh tests/MUnit/run-tests.sh --section Sampling  # OK=1 FAIL=0
#    then perturb one truth-table row -> must go red, and be restored

# 5. coverage, reported as a fraction with its denominator
python3 tools/verify_paper_artefacts.py          # per-table COVERED/UNCOVERED

# standing bars — must not move except where a delta is declared
zsh tests/MUnit/run-tests.sh --all               # >= OK=66 FAIL=0 (Sampling promoted)
make closure                                     # 8 members, all green
venv/bin/python -m pytest -q tests/analysis      # 32
(cd index-deconvolution && ../venv/bin/python -m pytest -q)          # 146
for d in imp-causal-paper imp-prices imp-causalNet-paper imp-pathinfo-paper; do
  (cd $d && .venv/bin/python -m pytest -q -p no:warnings); done      # 28 / 97 / 47 / 41
(cd papers/method/manuscript_formal && pdflatex -halt-on-error method_paper.tex)
(cd papers/method/manuscript_computational && pdflatex -halt-on-error comp_paper.tex)
```

**Rules that hold throughout** (unchanged from the previous phase):

- **No copy is deleted** before an elementwise parity run against the survivor is
  committed as evidence; every collapse ships its guard in the same commit.
- **Promote the superset**, never the first copy found — a deficient copy was
  promoted once in this audit and had to be corrected.
- **Non-zero disagreement means stop**, not collapse. Two concepts need two names.
- **Every gate refuses on empty input and prints its denominator.**
- **Every intended delta declared** in `BASELINE.md` with its cause.
- **No number enters a document without its reference distribution in the same
  sentence.**
- **No Claude co-authorship in any commit.**

**Acceptance.** The fourth engine measured and adjudicated with evidence;
`VerificationSamples.m` carrying a predicate whose negative control was observed
to fire; the manifest describing the tree truthfully; `verify-paper` reporting an
honest coverage fraction rather than a catch-all; orphans labelled with evidence;
both small defects closed; every bar unmoved or its delta declared.

**Stop conditions.** No producer wiring for uncovered tables (decision: measure
only). No promotion of the ten archive-facing producers. Bio regeneration does
not start (blocked behind R4). R4.2–R4.5 do not start. R5 does not start
(`Q2.2` unresolved).
