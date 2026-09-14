# AUDIT04-F — the pivot ledger, the forwarder target, and the last Shannon sites

## Context

Three open items, all raised by the author on 2026-09-07 after commit `dd1b9ba`
(sumandos ruling gated). Each is stated below with the measurement that found it,
not with an assertion.

---

### Finding 1 — the propagation ledger cleared a tree it had not scanned

`GOVERNANCE/GLOSSARY.md` §8, propagation status table, line 266:

> | `index-deconvolution`, `imp-prices` finance code | many | **no change needed** — all finance-sense; already unambiguous in context |

**That row is false, and it is measurable.** Counted repo-wide, `pivot` occurs
**178** times. Classified by sense:

| sense | count | where |
|---|---|---|
| **method-sense — wrong, must go** | **17 in 7 files** | all inside `index-deconvolution/` plus one paper-code file |
| finance-sense | ~140 | `level2`–`level17`, `notebooks/`, `level5/pivots.py` |
| ordinary English | 21 | `PIVOT_HYBRID`, `PIVOT_CELL`, "pivotal distinction" |

The 2026-08-21/22 sweep renamed every method-sense `pivot` in the **Mathematica**
core and the papers, then exempted the whole `index-deconvolution` tree on the
assumption that it was all finance. The Python side of the Boolean method lives
in that tree. So the sweep reported *"zero `pivot` identifiers remain in the
Mathematica core"* — a true statement over a denominator that excluded the files
that still had the defect. This is the same comfortable-denominator failure the
manifest had (Wolfram-only) and the sumandos scan had (`.py/.m/.wl` only).

Worse, two of the seventeen are the ones GLOSSARY §1c **names as the source of
the confusion**:

- `index-deconvolution/level3/behaviour_table.py` — `"pivots_essential_bits"`, a
  dict key. A wrong identifier is a definition that cannot be argued with.
- `index-deconvolution/experiments/exp01_pivots_sumandos.py` — the filename §1c
  quotes: *"`exp01_pivots_sumandos.py` names a **set** and an **encoding** side by
  side, and reading that filename as a partition is how a lossless factorisation
  got mistaken for a lossy one."* The glossary diagnosed the filename and left it
  on disk.

**Author ruling, 2026-09-07:** *pivot* is a finance term and does not belong to
the decimals-and-sumandos vocabulary at all. This is stricter than GLOSSARY §3,
which still sanctions "pivot coordinates" inside the Boolean method, and stricter
than §8, which ruled `PIVOT_HYBRID` may stay. Both are superseded.

---

### Finding 2 — the forwarder target for the retired `D_v2` is wrong, measured

`Universal_D_v2_Encoder` now forwards to `row_run_index_set_length`. Reading its
canonical implementation (`imp-causalNet-paper` `causalbool_mirror`), it is a
**run-length code over each row's neighbour index set**. An alternating row costs
`n/2` runs — its maximum — while its algorithmic content is nearly nil.

Measured at `n = 16`, structured matrix versus 20–30 random matrices of
**identical edge count** (structured / random-mean, in bits; INV = the structured
object was called at least as complex as random):

| family | M1 row-run (current) | M3 schemata over index bits | M4 schemata over row set | BDM |
|---|---|---|---|---|
| checkerboard | 1050.5 / 563.9 **INV** | 23.0 / 690.0 ok | 43.2 / 330.4 ok | 34.3 / 489.9 ok |
| column stripes | 1050.5 / 568.4 **INV** | 8.2 / 721.3 ok | 21.1 / 330.4 ok | 34.2 / 485.2 ok |
| two diagonal blocks | 134.9 / 555.1 ok | 23.0 / 689.2 ok | 43.2 / 330.4 ok | 50.0 / 485.3 ok |
| band, in-degree 4 | 134.9 / 439.8 ok | 451.8 / 499.2 ok | 330.4 / 321.1 **INV** | 85.3 / 444.7 ok |
| band, in-degree 8 | 134.9 / 566.7 ok | 511.5 / 697.5 ok | 330.4 / 329.4 **INV** | 108.3 / 488.4 ok |

and on the chain test from the retirement note (12-node chain, 11 edges, versus
**200** random graphs with 11 edges — how often is random called simpler?):

| measure | chain | random simpler |
|---|---|---|
| M1 row-run | 88.81 bits | **14 / 200 = 7.0 %** |
| M3 schemata over index bits | 129.87 bits | **200 / 200 = 100 %** |
| BDM | 74.53 bits | **0 / 200 = 0.0 %** |

**Conclusion: there is no single adjacency-only encoding of our method that
survives every structured family.** M1 inverts on alternating structure; M3, the
one that looked most like the method (deconvolve the matrix cells into schemata,
don't-cares wherever they fall), inverts on chains, because the index-bit
coordinates depend on the node labelling; M4 inverts on bands *and* is lossy.
BDM is the only measure with zero inversions across all seven probes.

**And a derived fact that decides the design.** Our per-node measure
`schema_normal_form_length` (Variant E, `src/description_lengths.py:120`) costs a
node by `(n, gate, in-degree)` alone. `degree_preserving_swap` in
`Null_Generator_HPC` preserves in-degree by construction. Therefore **Σ_v
D_schema is exactly invariant under the null the experiment uses** and returns
the same number for the real network and every one of its nulls. Our
mechanism-side measure cannot answer a wiring question — not because it is weak,
but because a wiring question is not what it measures.

The standing directive (author, 2026-09-07) already prescribes the fix: *"the TWO
comparison measures are the INDEX-SET PROGRAM LENGTH and BDM."* So the encoder
reports **both**, and the null experiment decides on both. This is not a hybrid
measure — decision #96 forbids combining two measures into one number, and
nothing here is combined; two named measures are reported side by side.

---

### Finding 3 — the Shannon census has a precision hole and a recall hole

`audit/AUDIT04_E_measures/census_shannon.py` scans 628 files and reports 83
sites. Two defects:

- **Recall.** `src/stats/Mutual_Information_Analyzer.py` uses sklearn
  `mutual_info_regression` / `mutual_info_classif` — Shannon mutual information in
  nats, converted to bits — and the census does not see it, because it has no
  `p·log p` or frequency-table shape. It is consumed by
  `DepMap_Validation.py:1131` and steers the `PIVOT_CELL` branch of
  `Contingency_Monitor`.
  **Adjudication: it stays, relabelled.** It measures *dependence between a
  complexity score and a clinical outcome*, exactly as a correlation does. It is
  not a measure of complexity and never was, so it falls under the same rule as
  `H_total` and ZIP: a labelled statistic, never one of our measures.
- **Precision.** `src/analysis/Phase_Transition_Bio_Overlay.py` and
  `src/experiments/SimplicityV2_Nature.py` are flagged `count_to_prob` but
  contain no such computation on inspection. Every OURS site must be adjudicated
  individually and recorded, or the census number means nothing.

`src/integration/HierarchyEncoder.py` and `MotifEncoder.py` are flagged
`combinatorial_code`: `log2(C(n,k))`-style **enumerative** lengths, which are
legitimate description lengths and not Shannon. Confirmed, keep.

---

## Task 1 — amend the sibling GLOSSARY, then re-sync

`~/Documents/projects/series-deconvolution/GLOSSARY.md` is canonical;
`GOVERNANCE/GLOSSARY.md` is a copy and `tools/check_glossary_sync.sh` goes red on
local edits. Author permitted the sibling edit (as in the 2026-08-24 precedent).

1. New **§1e — *pivot* is a finance term**: the word is reserved for §1b's
   financial pivot. Inside the Boolean indexing method the vocabulary is
   **connected inputs** / **essential variables** (the coordinate sets),
   **decimal anchor** `P` and **decimal family** `L` (their encoding),
   **free coordinates** (the complement), **sumandos** `S` (the free
   coordinates' fillings, per §1d).
2. **§3 amended**: strike *"free coordinates — the complement of the pivot
   coordinates … is what the word 'pivot' is opposed to inside the Boolean
   method"*. The complement of the **connected inputs** is the free coordinates.
3. **§8 row for `index-deconvolution` corrected** from "no change needed" to the
   measured 17-in-7-files, with the note that the row was written without
   scanning the tree.
4. **§8 sub-heading "`PIVOT_HYBRID` is ordinary English — verified, keep it"
   superseded**, dated, with the author's reason: the word is retired outright so
   that no future reader has to adjudicate a sense. The earlier ruling is left
   visible as superseded, not deleted.
5. Recopy into `GOVERNANCE/GLOSSARY.md` with a refreshed provenance header;
   `tools/check_glossary_sync.sh` must exit 0.

## Task 2 — the method-sense rename (17 occurrences, 7 files)

Replacements are taken from the glossary's own naming table, never invented.

| file | was | now |
|---|---|---|
| `index-deconvolution/experiments/exp01_pivots_sumandos.py` | filename; `"experiment": "pivots_vs_sumandos"`; output `exp01_pivots_sumandos.json`; 3 docstring/print uses | `exp01_connected_inputs_and_sumandos.py`; `"connected_inputs_vs_sumandos"`; matching output name |
| `index-deconvolution/level3/behaviour_table.py` | key `"pivots_essential_bits"`; 3 docstring uses | key `"essential_variables"`, old key retained as a deprecated alias exactly as `sumando_bits` was |
| `index-deconvolution/src/deconvolution.py` | `PIVOT COORDINATES` ×2, and the §1c note quoting the pair | `connected inputs`; the note is rewritten to cite §1e |
| `index-deconvolution/src/causalbool.py:140` | "pivot-shifted cosets" | "anchor-shifted cosets" |
| `index-deconvolution/experiments/audit_legitimacy.py:93` | "connected (a pivot)" | "connected (an essential variable)" |
| `index-deconvolution/tests/test_deconvolution.py:42` | "Pivots vs sumandos" | "Connected inputs vs sumandos" |
| `papers/method/code/worked_example_7node/worked_example_7node.py:175` | "one pivot and N free weights" | "one decimal anchor and N free weights" |

The last one is **paper code** and was missed by the 2026-08-21 paper sweep,
which is further evidence for Finding 1. Re-run the script and confirm its
printed checks are unchanged apart from the wording.

The renamed result JSON is **regenerated**, not hand-edited; the superseded
`index-deconvolution/results/exp01_pivots_sumandos.json` is removed in the same
commit so two names cannot both resolve.

## Task 3 — finance-sense: prose only, identifiers and stored keys stay

GLOSSARY §3 already rules that `directional_change_pivots()` **keeps its name**,
and §7 rules that recorded results are not retro-edited. Measured, the stored
artefacts hold `"oos_gain_pivot"` (100 occurrences), `"n_meta_pivots"` (12) and
`"mean_oos_pivot"`; renaming those keys would invalidate recorded Level 5–17
values and force re-execution of the built notebooks.

So Task 3 is bounded to **prose**: in `index-deconvolution/level2`–`level17`
docstrings, README and print strings, bare *pivot* meaning a price turning point
becomes **financial pivot** on first use in each file. No identifier, no JSON
key, no notebook is re-executed. `bitacora/` is untouched under §7.

**This is narrower than "retire the word entirely" and the difference is stated
here deliberately**, so the author can widen it: widening means re-executing the
Level 5–17 notebooks and moving recorded numbers, which is a separate decision
from a terminology fix.

## Task 4 — retire `PIVOT_HYBRID` / `PIVOT_CELL`

| file | was | now |
|---|---|---|
| `src/pipeline/Contingency_Monitor.py` (7 sites) | `PIVOT_HYBRID`, `PIVOT_CELL` | `SWITCH_TO_HYBRID_ENCODING`, `SWITCH_TO_CELL_LINES` |
| `tests/Lev4/TSK-LEV4-INTEGRATION-001-Test.py` (3 sites) | same | same |

`results/bio/Contingency_Report.md` is a generated artefact and is regenerated,
not edited. `doc/newIntPaper/bioPlanLev-5.md` is an archive and stays under the
standing stop condition; `GOVERNANCE/VERIFICATION.md` line 235 is updated because
it is a live governance claim, not an archive.

Note: `TSK-LEV4-INTEGRATION-001` is **already declared RED** in
`VERIFICATION.md` (3 failed, 2 passed — the monitor returns `PUBLISH_EMERGENCE`
where the test expects `PIVOT_CELL` once and `CONTINUE` twice). That adjudication
is the author's and is **not** resolved here; only the names change, and the
declared failure must still be red for the same reason afterwards.

## Task 5 — the guard, verified by planting

Extend `tests/analysis/test_sumandos_definition.py` (it already owns the
vocabulary-of-the-method concept; a second file would be the defect this audit
removes) with a `pivot` arm:

- scans the same `OWNED` trees over the same `SCANNED_SUFFIXES`;
- fires on `pivot` **only inside the Boolean-method tree** — `src/`,
  `index-deconvolution/src`, `index-deconvolution/level3`,
  `index-deconvolution/experiments`, `tests/`, `papers/method/code` — leaving the
  finance levels, which are a declared exception with their reason;
- exception ledger for the files that *quote* the error to forbid it;
- **control**: "financial pivot" must NOT fire, and "connected inputs" must NOT
  fire, so the guard cannot push people back into saying nothing;
- refuses on zero files scanned and prints its denominator;
- **planted in the same commit** in a `.py`, a `.md` and a `.sh` — the sumandos
  guard's first plant slipped through on file type, so all three are checked.

## Task 6 — the forwarder reports both measures

`src/integration/Universal_D_v2_Encoder.py` `compute()` returns, additionally to
the retained `dv2` key:

```
"index_set_bits": row_run_index_set_length(cm)   # ours
"bdm":            bdm_2d(cm, below_floor="raise")
"measures":       ("index_set_program_length", "bdm")
```

`dv2` keeps carrying `index_set_bits` so the thirteen existing callers and the
stored artefacts resolve unchanged. Owner remains `src/description_lengths.py`;
nothing is reimplemented.

`Null_Generator_HPC.separation()` gains a second entry keyed `bdm` beside
`gap_bits` / `exceed`, and `Contingency_Monitor` **requires both to agree** on
falsification before it acts: disagreement is reported as `UNDECIDED`, never
silently resolved to one measure. A single measure deciding a project pivot is
what the retired `z = -999.0` default already did once.

## Task 7 — pin the two facts that were derived, not asserted

Both go in `tests/analysis/test_complexity_measures_are_algorithmic.py`, beside
the existing ordering arm at line 163:

1. **Density sweep on the ordering property.** The current arm tests one chain
   against random. Extend to the seven families in the Finding 2 table.
   `row_run_index_set_length` **is expected to fail checkerboard and stripes** —
   so the test asserts the measured direction *and* records those two as a
   declared, reasoned exception with their numbers, rather than being written to
   pass. A guard that hides a known inversion is worse than no guard.
2. **Σ_v D_schema is invariant under degree-preserving rewiring.** Build a
   network, apply `degree_preserving_swap`, assert the two schema lengths are
   **exactly equal**, with the docstring stating why this makes D_schema unusable
   for the null experiment. This is the fact that stops the forwarder being
   repointed at D_schema in six months.

## Task 8 — census: close both holes

- Add a `mutual_info` / `entropy(` / `scipy.stats.entropy` detector to
  `census_shannon.py` so the sklearn call is seen; re-report the denominator.
- Adjudicate all 31 OURS sites in a table in `GOVERNANCE/VERIFICATION.md`, each
  as **measure** (forbidden), **labelled baseline** (permitted, must be named as
  such in its output), **statistic** (permitted, e.g. MI) or **false positive**.
- `Mutual_Information_Analyzer` gains a module docstring stating it is a
  dependence statistic and not a complexity measure, and its result dict gains
  `"kind": "statistic"`.

---

## Verification

```bash
zsh tools/check_glossary_sync.sh                      # must exit 0 after Task 1
venv/bin/python -m pytest -q                          # 237 collected, no regressions
venv/bin/ruff check --output-format=concise .
zsh tools/run_closure.sh pure                         # 11/11
zsh tools/check_test_manifest.sh                      # 121/121, both languages non-zero
venv/bin/python tools/check_coverage_ratchet.py       # floor must not fall

# the guards must be observed to fail, in the same commit
#   plant "the pivot coordinates" into a .py, a .md and a .sh under src/  -> red x3
#   plant "financial pivot" and "connected inputs"                        -> stay green
#   revert row_run to the retired Shannon encoder                         -> ordering arm red

# regenerate, in this order, only after the above are green
venv/bin/python index-deconvolution/experiments/exp01_connected_inputs_and_sumandos.py
venv/bin/python papers/method/code/worked_example_7node/worked_example_7node.py
venv/bin/python src/experiments/Null_Generator_HPC.py --quiet   # 231 records, ~24 min
#   then results/bio/simplicity_v2_real.json (30) and results/lev3/setup001.json (3)
```

Every regenerated artefact is reported as **before → after with its reference
distribution in the same sentence**, and `GOVERNANCE/VERIFICATION.md` records the
move with its cause.

## Standing rules, unchanged

No Claude co-authorship — every commit uses
`git -c user.name="Alberto" -c user.email="albertohernandezespinosa@gmail.com"`.
British English, no contractions. No rewriting `doc/` or `workspaces/` archives.
No hybrid measure (decision #96). Replication packages `imp-*` are not converted
to our measure. The `.pth` file belongs to a sibling and is not edited.
`TSK-LEV4-INTEGRATION-001` stays declared RED; its adjudication is the author's.

## Out of scope, and why

The remaining AUDIT04 phases stand unchanged and are resumed after this:
Phase B Tier 1 (24 of 52 modules still at 0 %), Phase D mutants, Phase E
ledger and tag. The unexplained SIGSEGV and the ratchet's percentage-versus-
statement unit remain open.
