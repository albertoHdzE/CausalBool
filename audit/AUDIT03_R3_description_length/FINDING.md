# AUDIT03 / R3.1–R3.2 — the bio description length was not a description length

**Executed 2026-09-03 on branch `fixing`.** Reproduce with

```bash
HOME=$HOME /Applications/Wolfram.app/Contents/MacOS/WolframKernel -script \
  audit/AUDIT03_R3_description_length/dump_biometrics_grid.m
venv/bin/python audit/AUDIT03_R3_description_length/verify_description_length.py
```

Everything below is an execution result recorded in `verification.json`. Nothing
is asserted that the script does not measure.

---

## 1. The defect

`papers/method/code/complexity_analysis/complexity_analysis.py:238` charges an
in-degree field and says, in a comment, exactly why:

```python
cost += _log2(n + 1)                      # in-degree d, required for decodability
cost += _log2(max(1, math.comb(n, d)))
```

That field is what made `D_formula = 135.66` a valid length and superseded the
earlier 101.07. **`src/integration/bio_D_experiment.py` and
`src/Packages/Integration/BioMetrics.m` went straight to `log2 C(n, d)`**, so the
bio pipeline was still computing the superseded quantity — the one the author
remembered as wrong — eighteen days after the manuscript side was corrected.

This is not a rounding matter. A decoder reading such a stream cannot know how
wide the input-set field is, so the stream is not readable and the number is not
a description length. Both files are now fixed.

## 2. The proof, by decoder rather than by argument

The declared node language is four fields read in order:

| field | alphabet | bits |
|---|---|---|
| (a) gate type | one of `K = 12` | `log2 12` |
| (b) **in-degree `d`** | one of `n + 1` | **`log2(n+1)`** ← was missing |
| (c) input set `S` | one of `C(n, d)` | `log2 C(n,d)` |
| (d) parameters | one of `param_alphabet(gate, d, n)` | gate term |

The verifier derives the *lengths* from the *alphabet sizes* rather than writing
both down separately, so a Kraft sum cannot be taken over a space the cost does
not actually charge for. That is the specific way this class of error hides.

**G1 — Kraft, by exhaustive enumeration** (every input set listed, not counted):

| n | with the field | without (control) |
|---|---|---|
| 1–8 | **1.000000000000** | **exactly n+1** |

The corrected code is complete. The old one overshot by a factor of `n+1` — one
factor for each in-degree it never named. The control fires, so G1 is not inert.

**G2 — round trip.** Every description in the space decodes back to
`(gate, input set, parameters)` elementwise, with only `n` known in advance:
48 / 119 / 293 / 715 / 1,725 / 4,111 descriptions at n = 1…6, zero failures.
This is what establishes that the alphabets summed in G1 are the real ones.

**G2′ — the negative control, as a concrete collision.** Strip field (b) and
distinct nodes become byte-identical: at n = 3, **168** colliding descriptions;
at n = 4, **404**. The first is the plainest possible case — the field sequence
`[0, 0, 0]` reads *either* as `AND` on the empty input set *or* as `AND` on
`{0}`. No decoder can choose.

**G3 — four-way parity, cell by cell (U8).** 572 cells over n = 1…8, d = 0…n,
thirteen gate labels: `bio_D_experiment.py`, `BioMetrics.m` (dumped from the
kernel), `complexity_analysis.py`, and the declared language above.
**0 cells disagree.** Before the fix the two bio arms differed from the other two
in every one of the 572 cells.

## 3. What it cost the corpus

Measured through `load_processed_bio_networks` itself, not a private re-read of
the JSON — a shortfall computed by my own reading would measure my reading:

```
170 networks · 5,204 nodes · 27,756.72 bits never charged · 5.3337 bits/node
```

The plan's provisional figure of 34,469 bits was over 6,577 nodes, which is the
count in the `nodes` key across all 234 files. The loader keeps only the 170
files carrying `cm`, `gates` and `nodes` together, giving 5,204. **5,204 is the
number that matters; 27,756.72 supersedes 34,469.** (4,626 is a third count in
circulation — the nodes with a `gates` entry — and is the one quoted in
`CATALOGUE_EXPANSION.md`. Three node counts for one corpus is itself worth a
governance line.)

Largest per-network corrections:

| network | n | D old | D new |
|---|---|---|---|
| ginsim_2021-mammal-monocytes-dendritic | 94 | 1822.436 | 2440.002 |
| biomodels_MODEL2006170002 | 87 | 2448.748 | 3010.718 |
| ginsim_2019-mammal-cell-cycle-control | 87 | 2448.748 | 3010.718 |

Because the correction is `n·log2(n+1)`, it is constant within a network and
therefore **cancels in every knockout ΔD** — the knockout comparison holds `n`
fixed. It does **not** cancel in any comparison across networks of different
size, nor in `fold_reduction = mean_rand / D_bio`, which is a ratio and moves.

## 4. G5 — the reason the bio D is *still* not publishable

Fixing (b) was necessary and is not sufficient. The labels that actually reach
the cost function are:

```
CUSTOM 2486 · IDENTITY 762 · INPUT 729 · CANALISING 538 · AND 327
OR 280 · NOT 53 · NOR 26 · NAND 3
```

**3,977 of 5,204 nodes — 76.4% — carry a label that is not one of the twelve.**
The gate field charges `log2 12`, which indexes twelve labels; there is no
codeword for `CUSTOM`, `IDENTITY` or `INPUT`. The code cannot *write* three
quarters of the corpus, let alone decode it, and the default branch then charges
those nodes a polarity bit for a parameter they do not possess.

So G1–G3 prove a valid code **for the twelve-family language**, and the corpus is
largely outside that language. G5 is reported with its own verdict, separate from
R3.1/R3.2, so it cannot be mistaken for closed. It is the same gap AUDIT03/R4
(`REGULATORY_DNF`, 83.6% of the `CUSTOM` set) exists to close.

**No bio D or ΔD may be published until the language covers the corpus.**

## 5. Blast radius (R3.3) — recorded, not acted on

The same missing field survives in four further places. They are **not** touched
here: three of them move numbers pinned outside this audit, and R3.4 is an author
gate.

| # | location | status |
|---|---|---|
| 1 | `src/integration/bio_D_experiment.py` | **FIXED** |
| 2 | `src/Packages/Integration/BioMetrics.m` `encodeNodeCost` | **FIXED** |
| 3 | `tests/MUnit/Analysis/TSK-BIO-METRICS-001-Tests.m` | expected value updated, 28.5098 → 37.7975; delta is exactly 4·log2 5 |
| 4 | `tests/MUnit/Theory/TSK-THEORY-002-Tests.m` `encodeCostBits` | OPEN — private copy, emits `Dbits` to a committed artefact |
| 5 | `tests/MUnit/Theory/TSK-THEORY-004-Tests.m` `encodeCostBits` | OPEN — private copy, same |
| 6 | `imp-pathinfo-paper .../causalbool_mirror.node_description_cost` | OPEN — variant **B**; moves that package's published table |
| 7 | `src/description_lengths.py` `node_description_cost` | OPEN — the shared wrapper the T4.5 parity gate tests |
| 8 | `GOVERNANCE/DESCRIPTION_LENGTHS.md` §1 formula and §2 fixture | OPEN — variant B/D formulae and all four pinned toy values are pre-fix |

Already correct, and the reason the defect was findable at all:
`complexity_analysis.py` and `tests/MUnit/Mixed/TSK-MIXED-001-FormulaVsExhaustiveTests.m`.

Two further items surfaced on the way and are recorded rather than fixed:

- **`ComputeDescriptionLengthV2` has no decodability proof at all.** It drops the
  topology field on the claim that the motif and hierarchy fields already fix the
  wiring — but `dMotif` and `dHierarchy` are numbers *looked up* from the network
  association, not lengths emitted by any codec in this repository. `D_v2` is
  therefore not known to be a description length in any sense. Marked in the
  source at the point of the omission.
- **Input nodes are priced differently in the two languages.** The three WL
  scripts override `encodeNodeCost[_, "Input", _, _] := 0`, matching the
  `gType = "Input"` they set themselves; the Python loader labels the same nodes
  `"INPUT"` and charges them the full default cost. Both are internally
  consistent; together they are a cross-language divergence over 729 nodes.
- **The T4.5 parity gate cannot see Wolfram drift.** Its header-delta check
  compares two numbers *stored in the fixture* rather than re-deriving `D` from
  the kernel, so `BioMetrics.m` can change without the gate noticing. It is
  passing today on a value that is now stale. Belongs in R6.

## 6. Verdicts

| gate | verdict |
|---|---|
| G1 Kraft (+ control) | **PASS** |
| G2 round trip | **PASS** |
| G2′ collision control | **PASS** (fires) |
| G3 four-way parity, 572 cells | **PASS**, 0 disagreements |
| G4 corpus shortfall | measured: 27,756.72 bits |
| **G5 language coverage** | **FAIL — 76.4% of the corpus is outside the declared language** |

R3.1 and R3.2 are closed. R3.3 is enumerated above. R3.4 remains at the author
gate and is now known to be blocked behind R4 as well: regenerating bio numbers
under a language that cannot express three quarters of the corpus would replace
one invalid figure with another.
