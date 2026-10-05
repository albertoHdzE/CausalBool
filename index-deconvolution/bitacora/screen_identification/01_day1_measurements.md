# Entry 01 — Day 1: corpus, S2, S3a, S3b measured; S1 running

Date: 2026-09-29
Status: S2, S3a, S3b complete; S1 still running; verdict not yet computed.

## 0. Freeze check

`git log -- index-deconvolution/PROTOCOL_screen_identification.md` returns
`dcc1d59e` (2026-09-29 10:04). No measurement preceded the freeze.

## 1. Corpus (`corpus/manifest.json`)

- 35 synthetic networks: `random_network(n, seed, max_arity=3, gate_pool="core")`,
  n in {10, 15, 20, 30, 50, 100, 200}, 5 seeds per n, seed = 1000·n + s.
  `gate_pool="core"` excludes CANALISING because `exact_query_representation`
  does not accept it.
- 20 biological models (n from 4 to 87), selected from the 50 of 236 files in
  `data/bio/processed/` that are Boolean and load in every tool. 156 files
  were rejected at conversion (multivalued or threshold logic, or no logic),
  30 as duplicates.
- Load check: the forward map of each tool (ours, BoolNet, PyBoolNet, dd, Z3)
  equals `causalbool.step` on 64 pinned random states, for all 55 entries; ours
  also by canonical diagram identity over all 2^n states.

Two loader decisions taken before any measurement: GINsim's `X:1` is read as
`X` when the model has no level of 2 or more; rules `TRUE`/`FALSE` are
constants. Both had caused Boolean models to be rejected.

## 2. S3a — one-step causal questions (`s3a_one_step.json`)

Question: which assignments of which inputs make 1, 4 or 8 chosen nodes take
chosen values at the next step. Networks: the 35 synthetic ones, in-degree at
most 3.

Guards: adapter matches `causalbool.step` 2240/2240; sampled rows of our answer
satisfy the query 572/572; the number of satisfying assignments agrees across
ours, CUDD and Z3 on 105/105 questions.

At n = 200, 8-node questions, per network (ours assignments × support; CUDD
nodes; ours ms; CUDD ms):

| assignments | support | CUDD nodes | ours | CUDD |
|---|---|---|---|---|
| 7203 | 17 | 45 | 25.62 ms | 0.187 ms |
| 3024 | 18 | 62 | 12.07 ms | 0.221 ms |
| 567 | 14 | 50 | 1.57 ms | 0.148 ms |
| 216 | 14 | 84 | 0.63 ms | 0.183 ms |
| 972 | 17 | 128 | 3.06 ms | 0.180 ms |

**Reading.** Both answers are exact and equal in count. The difference is the
form of the answer. `exact_query_representation` returns the satisfying
assignments as an explicit list over the support (7203 rows of 17 bits); CUDD
returns a shared diagram (45 nodes). The list grows as the product of the
local choices; the diagram shares common sub-assignments. This measures the
OUTPUT FORM of that one function, not the index-set method as such: the
method's schema form (don't-care positions, GLOSSARY §1d) is also a compressed
form, and this function does not produce it.

Neither arm touches the 2^200 states: both work only on the ~17 inputs the
query depends on. Locality is not what separates them.

## 3. S3b — multi-step questions (`s3b_multi_step.json`)

- Fixed points: PyBoolNet and BoolNet answer all 55 networks, milliseconds,
  counts agree 55/55.
- All attractors: our arm is `num_attractors` (`src/reprogramming.py`), which
  loops over all 2^n states, so it was run only up to n = 24. BoolNet
  (SAT-based) and PyBoolNet time out (60 s) on most networks at n ≥ 100.
- Reachability within 3 steps: PyBoolNet (NuSMV) 1.1–1.8 s at n = 200; Z3
  bounded model checking about 0.05 s; the two agree 110/110.

**Who is wrong in the 20 disagreements on attractor counts.** PyBoolNet, in
all 20. Ours and BoolNet were both run on 27 networks and never disagree;
every attractor reported by any tool was checked state by state with
`causalbool.step` and none failed. PyBoolNet reported fewer attractors in all
20 cases, and on 4 of them it declared its own answer complete. Its attractor
search is built on trap spaces, which is sound for asynchronous update and
misses synchronous cycles.

## 4. S2 — identification by queries (`s2_queries.json`)

Akutsu 2003 (strategic queries) has no released software; replaced per
PROTOCOL §2 by Akutsu 1999 (random samples), solved by BoolNet with maxK = 3.
Only 1 of 15 networks at n ≥ 50 was identified within 2 × Q_LB (H1). At
n = 100, Q_LB = 26 and the queries needed were 63 to 81. Guard:
`verify_forward` equals its symbolic twin on 126/126 checks. Our arm: none
exists.

Caveat: the headroom is measured against random sampling. The stronger
competitor (chosen queries) could not be run.

## 5. S1 — full table (running; `s1_full_table.json`)

So far `deconvolve` is exact wherever run; 0.27 s against about 15 s for
BoolNet at n = 15; 14.6 s against a BoolNet timeout (> 600 s) at n = 20.

## 6. Questions raised by the author on reading Day 1, and open items

1. *Is the S3a test fair to the method?* The corpus has in-degree at most 3
   and n at most 200 because the frozen protocol says so. The author asks for
   n ≥ 300 and complex networks (higher in-degree, mixed gates). This would be
   a dated amendment to the protocol, not a silent change.
2. *Face-to-face check of answers.* So far the counts agree and sampled rows
   verify. A full set-equality check (every row of ours is a path of the CUDD
   diagram and vice versa) has not been run. It is cheap and should be.
3. *Answer size.* The comparison should be repeated with the method's schema
   form of the answer, if a function producing it for queries exists; the
   current function returns the explicit list.
4. *Should the method run on a decision-diagram engine?* The repository
   already has a symbolic backend for deconvolution
   (`src/deconvolution.py`: `deconvolve_root`, `verify_forward_symbolic`, over
   the engine in `doppel-challenge/`). Whether the query engine should use it
   is an author decision.
5. *"Ours is exhaustive" for attractors.* The METHOD represents the whole
   behaviour compactly; the existing FUNCTION `num_attractors` does not use
   that representation, it enumerates states. PROTOCOL §1 records this
   distinction. An index-based attractor search does not exist and was not
   built here.
