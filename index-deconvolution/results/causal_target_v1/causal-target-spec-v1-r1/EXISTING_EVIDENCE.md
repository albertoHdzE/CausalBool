# Existing evidence — reconciliation (`causal-target-spec-v1-r1`)

Executor: Claude Code, 2026-10-04. Read-only. Nothing below was re-run; every empirical
statement cites a saved artifact, and every capability cites a function in source. Files read
beyond the packet's required inputs are listed in `evidence_manifest.json` with hashes.
Codebase-graph tools were not used; source was inspected with grep and sed (the fallback is
recorded in the manifest).

## 1. Claims, access and status

| # | line of work | claim as stated | input access actually assumed | demonstrated result (artifact) | limitations that travel with it |
|---|---|---|---|---|---|
| E1 | full-table deconvolution | "given only the output repertoire … recovers per node the exact pair (I_c, f)" (`src/deconvolution.py` module docstring; `README.md` l.3–5) | regime 3: the complete labelled 2^n × n transition table, known bit order, noiseless, stationary, autonomous | 200/200 synthetic networks n = 7–10 reproduce their repertoire; 135/135 Python–Wolfram forward parity over all twelve families (`README.md` l.130–150, historical snapshot); S1: exact on 27/27 networks n ≤ 20 (`bitacora/screen_identification/02_verdict.md`) | Recovers the **function and its essential set**, not syntax or declared edges (`bitacora/01` §"Why the inversion is exact", items 1–4; canonical naming is an equivalence class, l.90–94). Biological 8/8 is a round-trip consistency certificate, not discovery (`README.md` l.153–160). Ingestion is 2^n (`root_from_behaviour`, `deconvolution.py:539`). |
| E2 | trajectory route (cellular automata) | "when the trajectory covers every local neighbourhood the recovered rule is exact" (`src/ca_deconvolution.py` docstring) | regime 2 plus a **structural assumption**: locality radius ≤ `max_radius`, shared rule, labelled cells | 12/12 elementary rules, global-map equality (`README.md` l.151) | Smallest consistent radius is a selection rule (`deconvolve_ca_cell`, `_consistent`); identification holds only under the locality bound and coverage. |
| E3 | S2 query recovery (screen) | "Headroom exists: identification by queries is not near-optimal" (`results/screen_identification/VERDICT.md`, H1) | **i.i.d. uniform random states** with successors (`experiments/screen_s2_queries.py` l.12–17, l.113); no chosen-query learner was run | best lenient m at n ≥ 50 is 42–112 samples against Q_LB 23–29; 1/15 within 2·Q_LB (`results/screen_identification/s2_queries.json`, `h1`) | See §2: Q_LB is a valid worst-case bound for the counted class after a recount, but H1 compares a **worst-case** bound with **per-instance** stopping points of a **non-certifying, non-adaptive** learner. "Headroom" is therefore not established; the gap may be bound looseness. Akutsu 2003 [9] has no software and was not run (`02_verdict.md` qualification 1). |
| E4 | S3a/S3b questions about a supplied model | S3a: no headroom (CUDD < 1 s at n = 200); S3b attractors: headroom, our arm exhaustive (`VERDICT.md`) | the model is **given** (not recovered); questions are forward computations | as in `VERDICT.md` and `table.md` | Forward querying of a known model is not identification and is not causal evidence about a black box. S3a size comparison measured the explicit-list output, not the schema form (`02_verdict.md` q.3). |
| E5 | HID / dictionary compression (hierarchy line) | best R and best O never shorter than A0 on 96 strings (`review_closure/representation-review-v1-r1/SYNTHESIS.md` §2) | regime 1: unlabelled finite bit strings; no state coordinates, no interventions | 0/96 shorter for both; STOP accepted as a research-priority decision (`supervision/…-closure/REVIEW.md`) | A compression result over strings. It identifies no mechanism, and the review explicitly leaves the causal-recovery target unspecified. Rule kinds in archives are witnesses of representation, not of a search path or of causation. |
| E6 | order discovery (uncontrolled sequences) | objective: behaviour tables, compressed rules, out-of-sample forecast beating a shuffle (`PROTOCOL_order_discovery.md` §4, §8) | regime 1, with the binarisation chosen by the analyst (§2) | finance: no deterministic Boolean network (contradiction 0.66, 0/9 exact) versus control 9/9 (`README.md` l.163–165); clock forecast results recorded in project memory, not re-read here | Success criterion is compression plus forecasting. Neither is causal identification (protocol §1 of this phase). Its "universality" framing (§1 "extension of algorithmic information theory into the long-term regime") is a programme aim, not a theorem. Its *pivot/residual* vocabulary is a finance/no-look-ahead notion (GLOSSARY §1, §1e) and is **not** imported here. |

Owners identified (not modified): `src/deconvolution.py` (`essential_variables`, `reduce_column`,
`identify_gate`, `deconvolve`, `verify_forward`, symbolic twins), `src/causalbool.py` (`step`,
`repertoire`), `src/ca_deconvolution.py`, `src/reprogramming.py` (`knockout`, `num_attractors`),
`src/network_generator.py` (`random_network`). **Current source has no chosen-query (oracle-mode)
learner**: a grep for oracle/membership/query in `src/`, `experiments/`, `hierarchy/` finds only
the screen scripts and the hierarchy's compression test oracle (`hierarchy/tests/oracle.py`,
"exhaustive minimum over a deliberately small language"), which is unrelated. So the absence
recorded in the 2026-09-29 screen still holds on 2026-10-04, checked rather than inherited.

Overlapping active work: the git status at preflight shows uncommitted edits by others in
`index-deconvolution/hierarchy/`, `src/bnet.py`, `src/ca_deconvolution.py`, notebook 17 and the
luminal tree (`preservation_before.json`). None is in this run's output directory; none was read
for conclusions except `ca_deconvolution.py` (read-only, current working copy, hashed in the
manifest).

Intervention semantics already present in source, kept distinct: `reprogramming.knockout`
**replaces a node's update function by a constant** (mechanism replacement: x_i(t+1) = c for all
t; x_i(t) is untouched at the instant of intervention). That is not the same as **resetting the
state before a step** (W4), nor as clamping both. TARGET_CONTRACT §4 names all three.

## 2. Audit of `PROTOCOL_screen_identification.md` §3 (Q_LB)

**What the formula counts.** `Q_LB = ceil(log2 C(n,k) + 2^k)` is log2 of C(n,k)·2^(2^k): one
**padded support** of exactly k declared coordinates times **every** Boolean table on it. These
objects are (support, table) pairs, i.e. syntactic hypotheses, not distinct functions. A function
with fewer than k essential inputs appears under many supports (a constant under all C(n,k)).

**What the corpus contains.** `random_network` draws arity uniformly in 1..max_arity (= 3), or
1/2 for unary/binary gates, from a 12-family gate pool, with self-loops possible
(`rng.sample(range(n), arity)` includes k). So the truth class is "at most 3 declared inputs,
restricted gate family", and declared inputs may be functionally redundant (README: degenerate
CANALISING). Degree is **at most** k, not exact.

**What a query reveals.** One state query returns the full successor: n bits, at most 2^n outcomes.
Because the network class is a product of per-node classes, N_net = N_node^n.

**A valid bound for a declared finite class.** Let C(n,k) be the class of networks whose every
node computes a function with at most k essential variables, labels and bit order known, chosen
state-successor queries, adaptive, exact functional identification required in the worst case.
Let E_j be the number of Boolean functions with exactly j essential variables (E_0..E_3 =
2, 2, 10, 218, checked in `witness_results.json`). The node class has
N(n,k) = Σ_{j≤k} C(n,j)·E_j distinct functions. An adaptive learner is a decision tree whose
internal nodes have at most 2^n children; it must reach distinct leaves for distinct networks, so
2^(nQ) ≥ N(n,k)^n, i.e. **Q ≥ ⌈log2 N(n,k)⌉** in the worst case over the class.

| n (k = 3) | padded C(n,3)·256 | distinct N(n,3) | log2 padded | log2 distinct | screen Q_LB | valid bound |
|---|---:|---:|---:|---:|---:|---:|
| 50 | 5,017,600 | 4,285,152 | 22.26 | 22.03 | 23 | 23 |
| 100 | 41,395,200 | 35,300,302 | 25.30 | 25.07 | 26 | 26 |
| 200 | 336,230,400 | 286,520,602 | 28.32 | 28.09 | 29 | 29 |

The padded count overstates the distinct count by 17% at each n, about 0.23 bits; the ceiling
absorbs the difference at every n where H1 was applied. **The integers used by H1 are therefore
valid worst-case lower bounds for C(n,3)**, but only by the coincidence of rounding, not by the
screen's argument: an upper bound on a hypothesis count (padded pairs) does not give a lower bound
on queries. Hand count on two inputs (W2 attachment, checked): k = 1 has 6 distinct functions
against 8 padded pairs; the n = 2 network class has 36 members, so Q ≥ ⌈log4 36⌉ = 3, and the
non-adaptive set {00, 01, 10} attains 3 while no pair of queries suffices. That tiny case is tight;
nothing here says the bound is tight at n ≥ 50.

**What H1 then measured, and why "headroom" does not follow.**
1. Q_LB is a worst-case bound over C(n,3); the 15 comparisons are per-instance stopping points.
   A specific instance can need fewer queries than the worst case, so a per-instance count above
   the bound is not a gap to the optimum on that instance.
2. The competitor was BoolNet on **random** samples, scored **leniently** (first listed solution
   exact, `screen_s2_queries.py` l.20–23). It neither chose queries nor certified uniqueness.
3. No upper bound (no algorithm) for chosen queries on C(n,3) was established. The ratio 1.8–3.9
   between measured random-sample counts and Q_LB may be entirely bound looseness. **The old
   2·Q_LB threshold is unvalidated as a headroom criterion** and is not used in this phase.
4. Biological models were not part of S2 (synthetic only, `screen_s2_queries.py` l.98). Hardware
   and access: BoolNet ran as an external R process with a 600 s probe limit; no chosen-query
   competitor exists in software. These preclude any niche statement.

The screen's NARROW verdict is unchanged and is not re-litigated; this audit qualifies one input
to it. Historical arithmetic is not new evidence of a competitive advantage.

## 3. Terminology used in this phase

Connected inputs = essential variables of the node's function (GLOSSARY §1a, `essential_variables`
docstring). Free coordinates are those a given schema does not depend on; sumandos are the
fillings of a schema's own don't-care positions (§1d). These are description objects. None of them
is a *causal variable* in the sense of TARGET_CONTRACT. *Pivot* and *residual* are not used (§1e).
"Complexity" here means only an algorithmic description length under DESCRIPTION_LENGTHS (e.g.
`D_schema`); no entropy or BDM sum enters any criterion of this specification. GLOSSARY §1 uses
"causal" for **no look-ahead** in time; this phase uses "causal" for **interventional** claims.
The two senses are different and are kept apart.
