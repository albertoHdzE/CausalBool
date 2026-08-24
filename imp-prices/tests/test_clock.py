"""The Phase 2 clock forecast and its null (ledger B6).

The null is the load-bearing part, so most of these tests are about the null
rather than about the forecast.
"""
from __future__ import annotations
import numpy as np, pytest
from imp_prices.clock import clock_forecast, forecast_vs_null, return_shuffle
from imp_prices.pivots import directional_change, legs, short_wait_target


def test_return_shuffle_preserves_the_marginal_and_destroys_the_order():
    """The Level 5 lesson: a null must keep the fat tail and kill only time order."""
    rng = np.random.default_rng(0)
    p = 100 * np.exp(np.cumsum(rng.standard_t(3, 3000) * 0.01))
    s = return_shuffle(p, np.random.default_rng(1))
    r0, r1 = np.diff(np.log(p)), np.diff(np.log(s))
    np.testing.assert_allclose(np.sort(r0), np.sort(r1), atol=1e-12)   # same marginal
    assert s[0] == pytest.approx(p[0])
    assert abs(np.corrcoef(r0, r1)[0, 1]) < 0.2                        # order destroyed


def test_the_null_is_run_through_the_whole_pipeline():
    """Surrogates must be re-detected, not reuse the real pivot times."""
    rng = np.random.default_rng(2)
    p = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 2000)))
    real = len(directional_change(p, 0.05))
    surr = [len(directional_change(return_shuffle(p, rng), 0.05)) for _ in range(30)]
    assert len(set(surr)) > 1, "surrogate pivot counts must vary; else detection was reused"
    assert min(surr) <= real <= max(surr), (
        "real pivot count outside the surrogate envelope; "
        "detection semantics or theta drifted relative to the null pipeline")


def _zigzag(durations, amplitude=0.30, start=100.0):
    """A price path whose leg durations are exactly as specified."""
    p = [start]
    up = True
    for d in durations:
        target = p[-1] * ((1 + amplitude) if up else (1 - amplitude))
        p.extend(np.linspace(p[-1], target, d + 1)[1:])
        up = not up
    return np.asarray(p)


def test_a_predictable_clock_is_detected_against_the_null():
    """Power control, and the first version of it was wrong.

    A *perfectly periodic* clock is useless here: every wait equals the running
    median, so the short-wait target is constant, the base rate is 1.0 and the
    edge is 0 however well the model does. The control must therefore be a clock
    that is predictable but **not** constant. Alternating short and long waits
    give a target that is near-balanced and perfectly learnable.
    """
    durations = [8, 24] * 60
    p = _zigzag(durations)
    r = forecast_vs_null(p, 0.10, n_null=60)
    assert r is not None
    assert r["accuracy"] > 0.9, r
    assert r["excess_over_null"] > 0.15, r
    assert r["p_value"] < 0.05, r


def test_a_random_walk_does_not_beat_its_own_null():
    """Size control: geometric Brownian motion has no clock to find."""
    rng = np.random.default_rng(5)
    p = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 4000)))
    r = forecast_vs_null(p, 0.06, n_null=80, seed=11)
    assert r is not None
    assert r["p_value"] > 0.05, r


def test_forecast_is_deterministic_given_a_seed():
    rng = np.random.default_rng(6)
    p = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 2500)))
    assert forecast_vs_null(p, 0.06, n_null=40, seed=3) == \
           forecast_vs_null(p, 0.06, n_null=40, seed=3)


def test_b6_is_not_supported_on_the_monthly_panel():
    """Ledger C24. The pre-registered expectation is not met at this sample size."""
    from imp_prices import load_panel
    from scipy import stats
    panel = load_panel()
    cells = [forecast_vs_null(panel[s].to_numpy(), th, n_null=120)
             for s in ("WTI_Spot", "WTI_CL", "Brent_BZ") for th in (0.05, 0.08, 0.10)]
    cells = [c for c in cells if c]
    assert len(cells) == 9
    wins = sum(c["excess_over_null"] > 0 for c in cells)
    p = stats.binomtest(wins, len(cells), 0.5, alternative="greater").pvalue
    assert wins >= 6, "the direction should be consistently positive"
    assert p > 0.05, "but the sign test must not reach significance at this sample size"
