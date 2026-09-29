# Screen: identification and questions, against the established methods

**Version 1.0, written 2026-09-29, frozen at its first commit.** Changes after
that are appended as dated amendments. **Time box: 3 working days.** This is a
headroom screen, not a development project. It decides whether a product built
on deconvolution plus exact questions is worth building at all.

The landscape of competing methods, with references, is in
`RELATED_METHODS.md`. Read that first.

---

## 1. Why this screen exists

The arena-planner screen (`~/Documents/projects/arena-planner/VERDICT.md`)
stopped within 16 minutes: the problem had no headroom. The candidate niche now
under test is **"recover the exact mechanism of a black box from its behaviour,
then answer questions about it exactly"**. Established methods already do each
half: Boolean-network identification [8–10 in RELATED_METHODS] and symbolic
question answering [1–3, 12]. The screen measures whether any gap remains, and
whether we are the ones placed to fill it.

**The prior, stated before measuring.** The method and some of its current
implementations differ, and the screen must not confuse them.
- **Answering questions (forward) is not exhaustive.** The index-set query
  engine (`exact_query_representation`, in
  `papers/method/code/scalability_resource_envelope/`) answers a causal query
  from the query nodes' support alone. At n = 200, an 8-node query touches a
  median of 10 coordinates, leaves 190 free, and takes a median of 1.0 ms,
  where the full table would have 2^200 rows (`scalability_summary.json`).
- **Two current Python functions are exhaustive**, as implementations:
  - `deconvolve` (`src/deconvolution.py`) takes the full repertoire as input,
    and `essential_variables` scans all 2^n rows;
  - `num_attractors` (`src/reprogramming.py`) visits all 2^n states.
  They are used here only where no index-based arm exists yet.
- **The open question is the class of question.** One-step causal queries
  are the method's home ground. For questions over many steps (reachability,
  attractors), the support of the t-step map can spread with t. Whether the
  index-set answer stays small is exactly what S3 measures.

The screen must confirm or refute this prior with numbers, not assume either
outcome.

---

## 2. Settings

Synchronous Boolean networks with known ground truth:
- **synthetic networks** from `src/network_generator.py` (`random_network`), at
  n ∈ {10, 15, 20, 30, 50, 100, 200}, maximum in-degree k ≤ 3, 5 seeds per n;
- **published biological models** from `data/bio/processed/` (236 files).
  Select those that load into every tool, up to 20, and freeze the list with
  file hashes before measuring.

| Setting | What the learner may do | Our arm | Competitors |
|---|---|---|---|
| S1 full table | read all 2^n state–successor pairs (n ≤ 20) | `deconvolve` | BoolNet reconstruction [11]; best-fit extension [10] |
| S2 queries | ask the successor of chosen states, under a budget | **none exists**: an oracle-mode deconvolution would be new work | Akutsu 2003 strategic perturbations [9]; Akutsu 1999 random samples [8]; the counting lower bound of §3 |
| S3a one-step causal questions | the model is known; which assignments of which inputs make chosen nodes take chosen values at the next step | `exact_query_representation` (index-based) | the same question posed to a BDD package and to an SMT solver (Z3 [3]) |
| S3b multi-step questions | reachability within t steps, fixed points, attractors | index-based where it exists; otherwise `num_attractors` (exhaustive), labelled as such | PyBoolNet [12]; BoolNet attractor search [11] |
| S4 inputs and hidden state | Mealy-machine black box | not applicable (§5) | LearnLib [5]; out of scope |

A competitor that cannot be installed and run within 2 hours is recorded as
such, with the error, and replaced by the next one in its row.

---

## 3. Measurements

- **Exactness first.** Every recovered model is checked by `verify_forward`
  against ground truth. An inexact model scores nothing.
- **S1 and S2:** state queries or samples used to reach exact recovery, and
  wall time.
- **S2 lower bound.** Each query returns n bits. There are at most
  C(n, k) · 2^(2^k) hypotheses per node, so any exact learner needs at least

      Q_LB = ceil( log2 C(n, k) + 2^k )

  queries. For example, at n = 100 and k = 3 this is 26. The gap between the
  best measured competitor and Q_LB is the S2 headroom.
- **S3:** wall time per question, median of 3 runs, at each n, with a 60 s
  limit per question.
- Every number comes from a script writing `results/screen_identification/`.
  Seeds are pinned, and tool versions are recorded.

---

## 4. Gates, fixed now

- **H1: S2 headroom.** If the best competitor needs at most 2 × Q_LB queries
  at n ≥ 50, identification by queries is already near-optimal. There is no
  room, for us or anyone.
- **H2: S3 headroom, judged separately for S3a and S3b.** If a competitor
  answers every question of a class in under 1 s at n = 200, that class is
  already solved at the scales that matter. For S3a, the comparison with our
  index-based arm is then on time and on the size of the answer's
  description, not on feasibility alone.
- **H3: our standing.** In S1, where our arm exists, if `deconvolve` is not at
  least as fast as the best competitor at n ≤ 20, our exact-recovery advantage
  is not an advantage in time.

**Verdict:**
- **STOP** if H1 and H2 both show no headroom. The niche does not exist as
  stated.
- **NARROW** if headroom exists only where our current arms are exhaustive.
  The niche exists, but we are not yet placed to fill it. Next comes a written
  proposal for a query-mode or symbolic deconvolution, with its own protocol.
  Nothing is built here.
- **GO to a product protocol** only if headroom exists **and** one of our
  existing arms already leads there on exactness, time or queries.

---

## 5. Out of scope, deliberately

- **S4, systems with inputs and hidden state.** This is L*'s home ground
  (RELATED_METHODS §2). Our deconvolution assumes an autonomous, fully
  observed state. Adapting it is research, not a screen.
- **Time series and finance.** Markets offer no queries and no determinism
  (RELATED_METHODS §4). The CSSR comparison proposed there belongs to the
  time-series programme.
- **Clean room.** This screen is research and uses the owner code in this
  folder. If it ever leads to a product, the product is rebuilt clean-room
  from the published papers, as `arena-planner` was.
