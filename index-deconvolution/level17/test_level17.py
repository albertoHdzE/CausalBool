"""test_level17.py

Correctness of the scaling-law / gap-law machinery.
Deterministic; standard library + pytest only.
"""

from __future__ import annotations

import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from scaling import (gaps_of, gap_law, proliferation_exponent, _ll_powerlaw,  # noqa: E402
                     _ll_exponential, _ll_lognormal, normalised_gaps, ecdf_ks,
                     collapse_test, law_of_gaps)


def test_gaps_of():
    assert gaps_of([0, 3, 4, 10]) == [3, 1, 6]


def test_gap_law_recovers_exponential():
    # memoryless gaps with a large mean (discretisation negligible) -> exponential by AIC
    rng = random.Random(0)
    ev = [0]
    for _ in range(5000):
        ev.append(ev[-1] + max(1, round(rng.expovariate(1 / 60))))
    res = gap_law(ev)
    # exponential must at least beat lognormal (it is the true memoryless law)
    assert res["aic"]["exponential"] < res["aic"]["lognormal"]


def test_gap_law_recovers_lognormal():
    # lognormal gaps -> lognormal should win
    rng = random.Random(1)
    ev = [0]
    for _ in range(3000):
        g = max(1, int(math.exp(rng.gauss(2.0, 1.0))))
        ev.append(ev[-1] + g)
    res = gap_law(ev)
    assert res["law"] in ("lognormal", "powerlaw")   # heavy-tailed, not exponential
    assert res["law"] != "exponential"


def test_powerlaw_mle_recovers_alpha():
    # sample from a discrete-ish power law with known alpha via inverse transform
    rng = random.Random(2)
    alpha = 2.5
    xmin = 1.0
    x = [xmin * (1 - rng.random()) ** (-1 / (alpha - 1)) for _ in range(20000)]
    ll, par = _ll_powerlaw(x, xmin=xmin)
    assert abs(par["alpha"] - alpha) < 0.1


def test_proliferation_exponent_on_grid():
    # a series whose pivot count scales cleanly; just check it returns a finite E, R^2
    rng = random.Random(3)
    s = [100.0]
    for _ in range(8000):
        s.append(s[-1] * math.exp(0.02 * rng.gauss(0, 1)))
    res = proliferation_exponent(s, [0.01, 0.02, 0.04, 0.08])
    assert res["E"] > 0 and res["r2"] > 0.8


def test_lognormal_beats_exponential_loglik_on_heavy_tail():
    rng = random.Random(4)
    x = [math.exp(rng.gauss(1.5, 1.2)) for _ in range(2000)]
    lle, _ = _ll_exponential(x)
    lll, _ = _ll_lognormal(x)
    assert lll > lle


def test_normalised_gaps_have_unit_mean():
    ev = [0]
    import random as _r
    rng = _r.Random(5)
    for _ in range(500):
        ev.append(ev[-1] + rng.randint(1, 20))
    ng = normalised_gaps(ev)
    assert abs(sum(ng) / len(ng) - 1.0) < 1e-9


def test_ecdf_ks_bounds():
    assert ecdf_ks([1.0, 2, 3], [1.0, 2, 3]) == 0.0
    assert ecdf_ks([1.0, 1, 1], [9.0, 9, 9]) == 1.0


def test_collapse_tight_for_same_shape_different_scale():
    # same shape, different per-stock scale -> after normalising, collapse (small KS)
    import random as _r
    rng = _r.Random(6)
    per = []
    for scale in (20, 60, 200, 600):               # large enough that discretisation is negligible
        ev = [0]
        for _ in range(2500):
            ev.append(ev[-1] + max(1, round(scale * rng.expovariate(1.0))))
        per.append(normalised_gaps(ev))
    res = collapse_test(per)
    assert res["max_ks"] < 0.12                     # different scales collapse after norm
