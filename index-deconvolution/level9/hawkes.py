"""hawkes.py  (Level 9)

A short generative program for the clock: the exponential Hawkes self-exciting
point process.

The clock discovered in Levels 5-7 is a self-similar, clustered point process. The
Hawkes process is the canonical *short program* that produces clustering: each
event raises the intensity of future events through a kernel that decays in time,

    lambda(t) = mu + sum_{t_i < t} alpha * exp(-beta * (t - t_i)),

with three numbers -- a baseline rate mu, an excitation alpha, and a decay rate
beta. The ratio

    n = alpha / beta   (the branching ratio)

is the average number of events each event triggers. It is the order parameter: at
n = 0 the process is memoryless (Poisson); as n -> 1 it approaches a critical point,
where a single event sets off long, self-similar cascades. A near-critical Hawkes
reproduces long memory and fractal clustering from three parameters -- the
compression the Algorithmic-Probability instinct wants, aimed at the structure we
proved is compressible rather than at the incompressible price path.

Standard library only. The log-likelihood uses Ogata's O(N) recursion; the fit is a
coarse-to-fine grid search over (mu, n, beta), which is robust and needs no
optimiser.
"""

from __future__ import annotations

import math


def loglik(times: list[float], T: float, mu: float, alpha: float, beta: float) -> float:
    """Exact log-likelihood of an exponential Hawkes process on [0, T].

    LL = sum_i log(lambda(t_i)) - integral_0^T lambda(s) ds,
    with the intensity sum accumulated by the recursion
    A_i = exp(-beta*(t_i - t_{i-1})) * (1 + A_{i-1}),  A_1 = 0.
    """
    if mu <= 0:
        return -1e18
    n = len(times)
    if n == 0:
        return -mu * T
    ll = 0.0
    A = 0.0
    prev = times[0]
    # first event
    ll += math.log(mu)                       # A_1 = 0
    for i in range(1, n):
        dt = times[i] - prev
        A = math.exp(-beta * dt) * (1.0 + A)
        lam = mu + alpha * A
        if lam <= 0:
            return -1e18
        ll += math.log(lam)
        prev = times[i]
    # compensator: integral of lambda over [0, T]
    comp = mu * T
    if beta > 0:
        s = sum(1.0 - math.exp(-beta * (T - t)) for t in times)
        comp += (alpha / beta) * s
    return ll - comp


def poisson_loglik(times: list[float], T: float, mu: float) -> float:
    """Homogeneous Poisson log-likelihood (the memoryless null, n = 0)."""
    if mu <= 0:
        return -1e18
    return len(times) * math.log(mu) - mu * T


def _grid(lo: float, hi: float, k: int, log: bool = False) -> list[float]:
    if k == 1:
        return [(lo + hi) / 2]
    if log:
        a, b = math.log(lo), math.log(hi)
        return [math.exp(a + (b - a) * j / (k - 1)) for j in range(k)]
    return [lo + (hi - lo) * j / (k - 1) for j in range(k)]


def fit_hawkes(times: list[float], T: float) -> dict:
    """Maximum-likelihood fit by coarse-to-fine grid over (mu, n, beta).

    Parametrised by the baseline fraction f = mu / rate, the branching ratio
    n = alpha/beta in [0, 0.98], and the decay rate beta (inverse timescale).
    Returns mu, alpha, beta, the branching ratio, and the log-likelihood.
    """
    N = len(times)
    if N < 10:
        rate = N / T if T > 0 else 0.0
        return {"mu": rate, "alpha": 0.0, "beta": 1.0, "branching_ratio": 0.0,
                "loglik": poisson_loglik(times, T, rate), "n_events": N}
    rate = N / T

    fs = _grid(0.05, 1.0, 8, log=True)          # mu = f * rate,  f in (0,1]
    ns = _grid(0.0, 0.95, 10)                    # branching ratio
    betas = _grid(1.0 / 250, 1.0 / 1.0, 8, log=True)  # decay: timescale 1..250 days

    best = None
    for _ in range(2):                           # coarse then refine
        for f in fs:
            mu = f * rate
            for nb in ns:
                for beta in betas:
                    alpha = nb * beta
                    ll = loglik(times, T, mu, alpha, beta)
                    if best is None or ll > best[0]:
                        best = (ll, mu, alpha, beta, nb)
        # refine grids around the best
        _, mu_b, _, beta_b, nb_b = best
        fs = _grid(max(0.02, (mu_b / rate) * 0.5), min(1.0, (mu_b / rate) * 1.5), 6, log=True)
        ns = _grid(max(0.0, nb_b - 0.15), min(0.98, nb_b + 0.15), 8)
        betas = _grid(beta_b * 0.5, beta_b * 2.0, 6, log=True)

    ll, mu, alpha, beta, nb = best
    return {"mu": mu, "alpha": alpha, "beta": beta, "branching_ratio": alpha / beta,
            "loglik": ll, "n_events": N}


def oos_loglik(times_all: list[float], T_all: float, T_train: float,
               mu: float, alpha: float, beta: float) -> tuple[float, int]:
    """Held-out log-likelihood on (T_train, T_all], given params fitted on train.

    Uses the additivity of the point-process log-likelihood over disjoint windows
    (each with the full past): test_LL = LL_all([0,T_all]) - LL_train([0,T_train]).
    Returns (test_loglik, number_of_test_events).
    """
    train = [t for t in times_all if t <= T_train]
    ll_all = loglik(times_all, T_all, mu, alpha, beta)
    ll_train = loglik(train, T_train, mu, alpha, beta)
    return ll_all - ll_train, len(times_all) - len(train)


def simulate(mu: float, alpha: float, beta: float, T: float, seed: int = 0) -> list[float]:
    """Ogata thinning simulation of the exponential Hawkes process on [0, T]."""
    import random
    rng = random.Random(seed)
    times: list[float] = []
    t = 0.0
    while t < T:
        # upper bound on intensity just after t
        lam_bar = mu + alpha * sum(math.exp(-beta * (t - ti)) for ti in times)
        if lam_bar <= 0:
            break
        t += rng.expovariate(lam_bar)
        if t >= T:
            break
        lam = mu + alpha * sum(math.exp(-beta * (t - ti)) for ti in times)
        if rng.random() <= lam / lam_bar:
            times.append(t)
    return times
