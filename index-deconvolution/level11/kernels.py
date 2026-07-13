"""kernels.py  (Level 11)

Multi-scale (power-law) Hawkes -- open door #2 of the programme.

The Level 9 clock generator used a single-exponential kernel, one timescale. It
regenerated most of the fractal clustering but under-shot it (simulated Fano exponent
0.41 vs a real 0.49): one timescale cannot carry a genuinely self-similar process. The
market-microstructure literature (Bacry, Hardiman, Bouchaud) uses instead a *power-law*
kernel, phi(t) ~ t^-(1+gamma), which is scale-free and near-critical. We realise it the
standard way, as a sum of exponentials on a fixed geometric grid of timescales, so the
whole Level 9 O(N) Ogata machinery generalises component by component.

Kernel:  phi(t) = sum_p a_p exp(-beta_p t),   beta_p = beta_max * eta^-p  (K components).
To approximate a power law with exponent gamma we set a_p proportional to beta_p^(1+gamma);
the branching ratio is then

    n = sum_p a_p / beta_p = a * sum_p beta_p^gamma,

so given a target branching ratio n and exponent gamma the amplitude is
a = n / sum_p beta_p^gamma and a_p = a * beta_p^(1+gamma). The model has exactly three
free numbers -- baseline mu, branching ratio n, exponent gamma -- the same budget as the
single-exponential Level 9 kernel, but a self-similar shape.

Standard library only; deterministic; log-likelihood by a K-component Ogata recursion.
"""

from __future__ import annotations

import math


def geometric_timescales(k: int = 10, tau_min: float = 1.0, tau_max: float = 512.0) -> list[float]:
    """K decay rates beta_p on a geometric grid spanning [1/tau_max, 1/tau_min]."""
    if k == 1:
        return [1.0 / tau_min]
    betas = []
    for p in range(k):
        tau = tau_min * (tau_max / tau_min) ** (p / (k - 1))
        betas.append(1.0 / tau)
    return betas


def powerlaw_amplitudes(betas: list[float], n: float, gamma: float) -> list[float]:
    """Amplitudes a_p giving a power-law kernel of exponent gamma and branching ratio n."""
    w = [b ** gamma for b in betas]                      # sum a_p/beta_p = a * sum beta_p^gamma
    a = n / sum(b ** gamma / 1.0 for b in betas) if betas else 0.0
    # a_p = a * beta_p^(1+gamma); check: a_p/beta_p = a*beta_p^gamma, sum = a*sum beta^gamma = n
    return [a * (b ** (1.0 + gamma)) for b in betas]


def loglik_multi(times: list[float], T: float, mu: float,
                 alphas: list[float], betas: list[float]) -> float:
    """Exact log-likelihood of a multi-exponential Hawkes on [0, T].

    LL = sum_i log(lambda(t_i)) - integral_0^T lambda,  with one Ogata accumulator
    A_p per exponential component:  A_p(i) = exp(-beta_p*dt)*(1 + A_p(i-1)).
    """
    if mu <= 0:
        return -1e18
    n = len(times)
    if n == 0:
        return -mu * T
    K = len(betas)
    A = [0.0] * K
    ll = math.log(mu)                                    # first event, all A_p = 0
    prev = times[0]
    for i in range(1, n):
        dt = times[i] - prev
        lam = mu
        for p in range(K):
            A[p] = math.exp(-betas[p] * dt) * (1.0 + A[p])
            lam += alphas[p] * A[p]
        if lam <= 0:
            return -1e18
        ll += math.log(lam)
        prev = times[i]
    comp = mu * T
    for p in range(K):
        if betas[p] > 0:
            s = sum(1.0 - math.exp(-betas[p] * (T - t)) for t in times)
            comp += (alphas[p] / betas[p]) * s
    return ll - comp


def _grid(lo: float, hi: float, k: int) -> list[float]:
    if k == 1:
        return [(lo + hi) / 2]
    return [lo + (hi - lo) * j / (k - 1) for j in range(k)]


def fit_powerlaw(times: list[float], T: float, k: int = 10) -> dict:
    """ML fit of the power-law (multi-scale) Hawkes over (mu, n, gamma).

    Three free numbers, the same budget as the single-exponential kernel, on a fixed
    geometric grid of K timescales. Coarse-to-fine grid search; no optimiser.
    """
    N = len(times)
    betas = geometric_timescales(k)
    if N < 10:
        rate = N / T if T > 0 else 0.0
        return {"mu": rate, "n": 0.0, "gamma": 1.0, "betas": betas,
                "alphas": [0.0] * k, "branching_ratio": 0.0,
                "loglik": -rate * T, "n_events": N}
    rate = N / T
    fs = _grid(0.05, 1.0, 7)
    ns = _grid(0.0, 0.95, 8)
    gs = _grid(0.0, 1.5, 8)
    best = None
    for _ in range(2):
        for f in fs:
            mu = f * rate
            for n in ns:
                for g in gs:
                    alphas = powerlaw_amplitudes(betas, n, g)
                    ll = loglik_multi(times, T, mu, alphas, betas)
                    if best is None or ll > best[0]:
                        best = (ll, mu, n, g)
        _, mu_b, n_b, g_b = best
        fs = _grid(max(0.02, (mu_b / rate) * 0.6), min(1.0, (mu_b / rate) * 1.4), 5)
        ns = _grid(max(0.0, n_b - 0.12), min(0.98, n_b + 0.12), 6)
        gs = _grid(max(0.0, g_b - 0.25), min(2.0, g_b + 0.25), 6)
    ll, mu, n, g = best
    return {"mu": mu, "n": n, "gamma": g, "betas": betas,
            "alphas": powerlaw_amplitudes(betas, n, g),
            "branching_ratio": n, "loglik": ll, "n_events": N}


def oos_loglik_multi(times_all: list[float], T_all: float, T_train: float,
                     mu: float, alphas: list[float], betas: list[float]) -> tuple[float, int]:
    """Held-out log-likelihood on (T_train, T_all], params fitted on train."""
    train = [t for t in times_all if t <= T_train]
    ll_all = loglik_multi(times_all, T_all, mu, alphas, betas)
    ll_train = loglik_multi(train, T_train, mu, alphas, betas)
    return ll_all - ll_train, len(times_all) - len(train)


def simulate_multi(mu: float, alphas: list[float], betas: list[float],
                   T: float, seed: int = 0) -> list[float]:
    """Ogata thinning simulation of the multi-exponential Hawkes on [0, T]."""
    import random
    rng = random.Random(seed)
    times: list[float] = []
    t = 0.0
    K = len(betas)
    while t < T:
        lam_bar = mu + sum(alphas[p] * sum(math.exp(-betas[p] * (t - ti)) for ti in times)
                           for p in range(K))
        if lam_bar <= 0:
            break
        t += rng.expovariate(lam_bar)
        if t >= T:
            break
        lam = mu + sum(alphas[p] * sum(math.exp(-betas[p] * (t - ti)) for ti in times)
                       for p in range(K))
        if rng.random() <= lam / lam_bar:
            times.append(t)
    return times
