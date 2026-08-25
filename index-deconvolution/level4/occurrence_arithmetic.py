"""occurrence_arithmetic.py  (Level 4)

The behaviour table of a one-dimensional unit: given the occurrence set of a bit
column (the positions where it fires), discover the process columns -- the
arithmetic transforms that reproduce the set -- and read a compressed behaviour
rule from them.

In the controlled regime the process columns were ordinals, exponents,
place-values and a constant ratio (a geometric, self-similar spacing).  In an
uncontrolled sequence we do not assume those columns; we test which transforms are
actually present.  For a clustered occurrence set the columns that survive are:

  Column 1  DENSITY p            the base rate |O| / N  (the marginal place-value).
  Column 2  PERSISTENCE p11      P(next = 1 | current = 1).  When p11 > p the runs
                                 of ones are longer than chance: the ones cluster.
                                 The run lengths then follow a geometric law
                                 P(run = L) = p11^(L-1) (1 - p11), a closed form
                                 with a single parameter -- the direct analogue of
                                 the constant-ratio column (the ratio p11 between
                                 successive run-length probabilities is fixed).
  Column 3  MEMORY H             a Hurst exponent estimated by aggregated variance.
                                 H = 1/2 is memoryless; H > 1/2 is persistent,
                                 self-similar long memory across scales.

The behaviour rule read from these columns is a two-state description of the whole
string: the marginal p and the transition p11 (equivalently p00).  Its cost in
bits is compared with the i.i.d. cost; the difference is the compression the rule
achieves.  A rule counts as a discovery only when that difference is positive and
exceeds the shuffle's, i.e. it is strictly shorter than the occurrence set it
explains and shorter than chance would give.
"""

from __future__ import annotations

import math


def occurrence_set(bits: list[int]) -> list[int]:
    return [i for i, b in enumerate(bits) if b]


def gaps(bits: list[int]) -> list[int]:
    """Inter-occurrence gaps (differences of consecutive occurrence positions)."""
    o = occurrence_set(bits)
    return [o[i + 1] - o[i] for i in range(len(o) - 1)]


def run_length_encoding(bits: list[int]) -> list[tuple[int, int]]:
    if not bits:
        return []
    runs = []
    cur, count = bits[0], 1
    for b in bits[1:]:
        if b == cur:
            count += 1
        else:
            runs.append((cur, count))
            cur, count = b, 1
    runs.append((cur, count))
    return runs


def transition_probs(bits: list[int]) -> tuple[float, float, float]:
    """Return (p, p11, p00): marginal, P(1|1), P(0|0)."""
    n = len(bits)
    p = sum(bits) / n if n else 0.0
    n11 = n1 = n00 = n0 = 0
    for t in range(n - 1):
        if bits[t] == 1:
            n1 += 1
            n11 += bits[t + 1]
        else:
            n0 += 1
            n00 += 1 - bits[t + 1]
    p11 = n11 / n1 if n1 else 0.0
    p00 = n00 / n0 if n0 else 0.0
    return p, p11, p00


def _binary_entropy(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log2(p) - (1 - p) * math.log2(1 - p)


def description_length_gain(bits: list[int]) -> dict:
    """Bits saved by the two-state (Markov) rule over the i.i.d. description.

    L_iid    = N * H(p)                    -- code the string at its marginal rate.
    L_markov = model + N * H(next|current) -- code it at the conditional rate.
    The two-parameter model cost is charged honestly (two probabilities at
    resolution 1/N, i.e. log2(N) bits each), so a rule that does not genuinely
    predict cannot win by fiat.  The gain is the length of the occurrence-set
    description that the behaviour rule removes.
    """
    n = len(bits)
    p, p11, p00 = transition_probs(bits)
    # conditional entropy H(next | current)
    frac1 = p
    h_cond = frac1 * _binary_entropy(p11) + (1 - frac1) * _binary_entropy(1 - p00)
    l_iid = n * _binary_entropy(p)
    model_cost = 2 * math.log2(n) if n > 1 else 0.0
    l_markov = model_cost + n * h_cond
    return {
        "N": n,
        "L_iid_bits": l_iid,
        "L_markov_bits": l_markov,
        "gain_bits": l_iid - l_markov,
        "gain_per_symbol": (l_iid - l_markov) / n if n else 0.0,
    }


def hurst_aggregated_variance(bits: list[int], min_m: int = 2, max_frac: int = 8) -> float:
    """Hurst exponent by the aggregated-variance method.

    For block size m, the variance of the block means scales as m**(2H-2).  The
    slope of log(variance) against log(m) is therefore 2H-2, giving H.  For an
    independent series H = 1/2; H > 1/2 indicates persistent, self-similar memory.
    Returns 0.5 when the series is too short or degenerate to estimate.
    """
    n = len(bits)
    if n < 32 or sum(bits) in (0, n):
        return 0.5
    mean = sum(bits) / n
    ms, vs = [], []
    m = min_m
    while m <= n // max_frac:
        nblocks = n // m
        block_means = [sum(bits[k * m:(k + 1) * m]) / m for k in range(nblocks)]
        if len(block_means) < 2:
            break
        v = sum((bm - mean) ** 2 for bm in block_means) / len(block_means)
        if v > 0:
            ms.append(math.log(m))
            vs.append(math.log(v))
        m *= 2
    if len(ms) < 3:
        return 0.5
    # least-squares slope
    mx = sum(ms) / len(ms)
    my = sum(vs) / len(vs)
    num = sum((a - mx) * (b - my) for a, b in zip(ms, vs))
    den = sum((a - mx) ** 2 for a in ms)
    slope = num / den if den else -1.0
    return slope / 2 + 1  # H = slope/2 + 1  since slope = 2H - 2


def behaviour_table(bits: list[int]) -> dict:
    """The full one-dimensional behaviour table for a unit.

    Assembles the identified process columns (density, persistence, memory), the
    run-length reading, the geometric run-length law implied by the persistence
    column, and the description-length compression the behaviour rule achieves.
    """
    p, p11, p00 = transition_probs(bits)
    dl = description_length_gain(bits)
    runs_ones = [c for (v, c) in run_length_encoding(bits) if v == 1]
    mean_run = sum(runs_ones) / len(runs_ones) if runs_ones else 0.0
    return {
        "columns": {
            "density_p": p,
            "persistence_p11": p11,
            "persistence_p00": p00,
            "memory_hurst": hurst_aggregated_variance(bits),
        },
        "run_length": {
            "num_runs_of_ones": len(runs_ones),
            "mean_run_of_ones": mean_run,
            # closed-form geometric prediction of the mean run of ones
            "geometric_mean_run_pred": (1.0 / (1.0 - p11)) if p11 < 1.0 else float("inf"),
        },
        "persistence_excess": p11 - p,   # > 0 is clustering
        "compression": dl,
    }
