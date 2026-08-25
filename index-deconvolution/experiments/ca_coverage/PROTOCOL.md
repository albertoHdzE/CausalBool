# PROTOCOL — CA coverage sweep: identifiability envelope of CA→network deconvolution

**Pre-registration.** Committed BEFORE the run it governs (AUDIT_FIXING_PLAN_01
T4.3, AC-4.3a). No result-dependent changes permitted; deviations must be logged
as dated addenda below. Status: **FROZEN 2026-08-25.**

## Motivation

exp03 reports exact global-map recovery on 12 / 12 ECA rules under generating
assumptions (radius-1 local rule, homogeneous, periodic boundary) with pooled
initial conditions numerous enough to observe every neighbourhood. Exactness is
therefore *conditional on coverage*. This experiment quantifies the operating
envelope: recovery as a function of the fraction of neighbourhoods observed
before inversion.

## Fixed parameters (pinned)

| Parameter | Value | Source |
|---|---|---|
| Rules | [254, 90, 30, 110, 232, 204, 250, 150, 170, 57, 45, 73] | exp03 `RULES` |
| Width | 12 | exp03 default |
| Steps per diagram | 10 | exp03 default |
| Seeds | 20, seed0 ∈ {1 … 20} | task card |
| Coverage levels k | {4, 5, 6, 7, 8} distinct radius-1 window patterns at the interior cell (k/8 = p ∈ {0.50, 0.625, 0.75, 0.875, 1.00}) | task card p-grid |
| max_radius for deconvolver | 3 | exp03 call |

## Definitions

- **Interior cell** = column w//2; its radius-1 windows are the 3-bit patterns
  (left, centre, right) at each transition row t → t+1 of each diagram.
- **Observed pattern count** k(d) = |{3-bit windows seen in the pooled samples of
  the interior cell over all rows-transitions and all currently selected diagrams}|.
- **Greedy IC selection (per rule, seed, level):** rng = `random.Random((seed0,
  rule))` — draw candidate initial conditions sequentially; accept a candidate iff
  adding it increases k; stop as soon as k ≥ target level; if 40 consecutive
  candidates yield no increase, stop early and record achieved k.
- **Run** = one (rule, seed0, level) triple → deconvolve_ca(selected diagrams) →
  verify_ca with rule → record `global_map_exact` (full elementwise equality of
  the recovered network's exhaustive repertoire against the automaton's global
  map on all 2^12 states — never a cardinality or spot-row check), plus achieved
  k, support size, gate identity, trajectory_exact.
- **Recovery curve** per rule: fraction of the 20 seeds with global_map_exact at
  each level k.
- **Rule classification (post-hoc, declared now):** *saturating* = 20/20 seeds
  recover at k=8; *non-saturating* = otherwise. (All rules are expected to
  saturate at full coverage per exp03; failures below full coverage are the
  object of study.)

## Success criteria for the experiment itself

- Every number in `results/ca_coverage/summary.json` traces to this executed run;
  re-running `python experiments/ca_coverage/sweep.py` reproduces the file
  byte-identically (determinism check).
- One figure: recovery vs achieved coverage, one line per rule.

## Interpretation rules (pre-registered)

1. The headline claim "CA deconvolution recovers ECA exactly" may only be stated
   WITH its envelope, e.g.: *"exact global-map recovery holds once all eight
   radius-1 neighbourhoods are observed (20/20 seeds × 12 rules); below full
   coverage recovery degrades as measured in Fig. X."*
2. Any rule failing at k=8 must be root-caused before publication use (would
   contradict exp03 and trigger a deviation entry).
3. No smoothing, no aggregation across rules in the figure beyond per-rule lines.

## Deviations

- **D1 (2026-08-25, before any results were produced):** `random.Random((seed0,
  rule))` is not executable (Python seeds must be None/int/float/str/bytes).
  Implementation uses `random.Random(f"{seed0}:{rule}")` — same intent: a stream
  uniquely determined by (seed0, rule). No result-dependent change.
- **D2 (2026-08-25, first execution discarded before adoption):** reporting bug —
  recovery curves were binned by *achieved* pattern count instead of the
  pre-registered *target level*. Curves are now reported by target level;
  achieved-k retained per record as supplementary data. First execution's outputs
  are superseded and were regenerated.
- **D3 (2026-08-25, first execution discarded before adoption — scope correction):**
  the first implementation measured neighbourhood coverage at the INTERIOR CELL
  ONLY. Diagnosis of its output showed why this cannot define the envelope: with
  8/8 patterns at the interior cell but 0.75–0.88 coverage at other cells,
  unobserved truth-table entries default to 0 and the reconstructed network is
  globally wrong while remaining trajectory-exact — i.e. the quantity that gates
  identifiability is coverage pooled over ALL cells. Coverage is therefore
  redefined as **k = min over cells of the number of distinct radius-1 window
  patterns observed at that cell**, and the greedy selector targets this
  minimum. Per-cell coverage distributions are recorded for transparency.
  This is the reading the task card intended ("pooled ICs ensuring neighbourhood
  coverage"); no results from the discarded run are cited anywhere.
