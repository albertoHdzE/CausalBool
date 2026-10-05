# Plan — Holistic multi-level analysis of binary strings (Level 19, notebook 16)

## Context

Notebook 15 and bitacora 32 established that BDM credits only identical repetition, and only
where its fixed partition creates that repetition. The author's notes (pp. 12–20) propose the
opposite approach:

- look at the whole string at once;
- use words of variable length, up to the length of the target;
- describe a word as a parametric relation of another word (e.g. "shift a zero by i");
- read the order of the words from a network's dynamics (cycles and basins);
- recurse: patterns of patterns, a tree of trees.

The question is whether such a system finds descriptions that BDM cannot, **without finding
patterns in noise**.

### Positions settled in discussion (these govern the design)

1. **The criterion is the total description length, not the size of the pattern.** The author
   wants the largest pattern relative to the target. The whole string is always a pattern, but
   it costs |x|. So we search word lengths from 1 up to |x| and choose by the total two-part
   length: model + data, in bits, under one declared code. `repeat('01', 5000)` is then found
   at word length 2, at the first try, as the author wants.
2. **Repetition is not the same as a cycle (the author is right).** Repetition is a property of
   the *string* (e.g. AAAA XAXAX). A cycle is a property of the generator's *state space*.
   - A cycle implies repetition in the readout.
   - Repetition does not imply a cycle. Once an autonomous network enters a cycle it never
     leaves, so AAAA followed by (AX)³ needs either a transient that projects onto A, or more
     hidden state.

   The dynamics level therefore reports **transient and cycle separately**, and grammar-level
   repetition is a different level of description.
3. **Coverage is always achieved, so cost must decide.** Short words always cover a random
   string. A pattern counts only if it makes the total shorter than the literal. The
   incompressibility theorem says at most 2^-c of strings compress by c bits. That gives the
   null directly: claim structure only when the saving is at least c = 10 bits, so at most
   about 1/1000 of random strings can pass by chance.
4. **π is a pre-registered stretch case.** 128 binary digits of π have a short generator
   (BBP-type spigot) but look random to every block method. We record the expected outcome in
   advance: our language contains no arithmetic series, so the method should fail (total ≥
   literal). A pass would mean a bug or leakage. The case marks the limit of
   "compression = comprehension" for a given language.
5. **The observer scope is the model set S.** The total is K(S) + log|S|, the Kolmogorov
   structure function. The analysis reports which S (level and language) was chosen, so that
   the structure/noise split is explicit.
6. **OR-Tools, not arena-planner.** arena-planner's CLAUDE.md forbids importing anything from
   CausalBool and the reverse. We add and pin `ortools` in the root venv, and call CP-SAT
   directly, only for the dynamics level (author decision, 2026-10-01).

## Approach

### Reused (monolithic-code: located, not re-created)

| what | where |
|---|---|
| Elias-gamma lengths | `src/description_lengths.py::_gamma_len`; promote to public `gamma_len`, keeping a forwarder |
| `bdm_1d`, `ctm_1d` (baselines) | `src/description_lengths.py` |
| node description costs for the dynamics model | `node_description_cost` / `graph_gate_index_length` (Variant B) |
| `Network`, `step`, `evolve_network`, `apply_gate` | `index-deconvolution/src/causalbool.py` |
| reference baseline (labelled, never our measure) | `lz76_complexity` in `index-deconvolution/level3/behaviour_table.py` |

Glossary §1d/§1e terminology is respected: "sumandos" is used only in its schema sense.

### New code: `index-deconvolution/level19/`

**`holistic.py`.** The description language. Every description is a dataclass with
`decode() -> str` and `bits() -> float`, counted under one code: Elias gamma for integers,
fixed widths otherwise. The levels:

| level | description | cost |
|---|---|---|
| L0 | literal | header + \|x\| |
| L1 | repetition: word w × k, plus remainder | w ranges over lengths 1..\|x\| (the author's "bigger relative to the target") |
| L2 | segmentation into **variable-length** words: dictionary D + index sequence | dynamic programming over phrase boundaries; candidates are the factors of x with ≥ 2 occurrences, plus singletons |
| L3 | parametric dictionary entries | base word + operator (shift, rotate, complement, reverse, flip bit k) + parameter list; the shifted-zero family becomes one entry |
| R  | recursion | every index or parameter sequence (an integer string) is re-analysed by L0–L3 over its own alphabet, plus an arithmetic-progression rule; this builds the tree of trees, with depth capped at 4 |
| L4 | dynamics (Stage 2) | x = readout of a trajectory: network + x₀ + projection; CP-SAT finds node truth tables consistent with the trajectory for n ≤ 6 nodes; costs from the Variant-B node costs; reports transient length and cycle length |

`analyse(x)` returns the minimum-total description as a tree, with every candidate's total.
Exactness is enforced: a description whose `decode()` differs from x has no length.

**`exp42_holistic.py`.** The pre-registered experiment. It has a `--quiet` flag and writes
`results/exp42_holistic.json`.

**`test_level19.py`.**
- every level decodes exactly;
- the literal cost formula;
- `repeat('01', k)` is chosen at word length 2;
- shifted-zero A9 beats the literal;
- 50 seeded random strings never pass the c = 10 gate;
- the CP-SAT result reproduces a planted 3-node trajectory.

### Protocol first: `index-deconvolution/PROTOCOL_holistic_analysis.md`

Frozen and committed before any run. It records the code, c = 10, the corpus, the gates and the
expected outcomes.

**Corpus, all deterministic:**
- `repeat('01', k)` for k = 8 and 5000;
- A, A9, AX, AXM, P1–P3 (bitacora 32);
- the k-zeros families;
- the page-12 counting string `000001…111`;
- the author's variable-word case: AAAA XAXAX, with '01' and a 4-bit word at irregular
  positions;
- a planted 3-node trajectory with a transient into a cycle, read through a projection;
- 128 binary digits of π;
- planted random strings, 200 seeds at each of lengths 24, 48, 256 and 1024.

**Gates:**

| gate | condition |
|---|---|
| G-random | at most 1% of the random strings save ≥ 10 bits |
| G-planted | every structured case saves ≥ 10 bits and recovers its generating level (e.g. period 9 for A9, the parametric shift for AX, the cycle for the trajectory case) |
| G-π | recorded; expected FAIL |
| G-BDM | every measure is compared as a ratio to its own random baseline at the same length (the common coordinate from notebook 15); BDM is minimised over block 1..12 and phase |

### Stages and checkpoint

- **Stage 1:** promote `gamma_len`; L0–L3 + R; protocol; tests; exp42 without L4; notebook 16
  sections 1–5. **Stop, and show the author the gate table.**
- **Stage 2:** pin `ortools` in the root venv; L4; rerun exp42 with L4; notebook 16 section 6
  (cycles against repetitions); bitacora 33.
- **Also:** append the pp. 12–20 assessment and these settled positions to bitacora 32.

### Notebook 16 (`notebooks/build_16.py` → `16_holistic_levels.ipynb`)

Same builder pattern as `build_15.py`, using `_nblib` and `BOOTSTRAP`.

1. Render each corpus object.
2. The level ladder for one string: every candidate's total, and why the winner wins.
3. The tree of trees for P2/P3 and AAAA XAXAX.
4. The planted-random gate, with the 2^-c envelope drawn.
5. Against BDM, each measure as a ratio to its random baseline.
6. (Stage 2) Cycle against repetition: the state graph with transient and attractor, drawn
   next to the readout string.

## Verification

- `venv/bin/python -m pytest -q --tb=no tests/analysis/test_description_lengths_values.py`
  (the `gamma_len` forwarder must keep the existing tests green);
- `venv/bin/python -m pytest -q index-deconvolution/level19`;
- `venv/bin/python index-deconvolution/level19/exp42_holistic.py --quiet` prints the gate
  table; G-random and G-planted must pass, and G-π is reported as it falls;
- the notebook is executed with nbconvert on the `causalbool` kernel and must have 0 error
  outputs; figures are rendered and inspected before any number enters prose;
- ruff `--output-format=concise` on the new files;
- nothing is committed unless the author asks.
