"""joint_law.py  (Level 7)

The joint law of the two occurrence coordinates of a leg: its duration dt and its
signed value change dv.  Level 5 studied their marginals; here we study how they
couple.

Two physically motivated questions:

  * Within a leg, how does the distance travelled scale with the duration?  For a
    diffusion |dv| ~ dt**H with H = 1/2 (Brownian).  The log-log slope of |dv|
    against dt is a within-leg diffusion exponent; H below 1/2 is sub-diffusive
    (the excursion travels less than a random walk of the same duration), H above
    1/2 super-diffusive (trending).

  * Across legs, does a long calm precede a large move (or a large move a long
    rest)?  The cross-correlations corr(dt_i, |dv_{i+1}|) and corr(|dv_i|,
    dt_{i+1}) answer it.

Both are compared with the return-shuffle null, whose legs are those of a random
walk with the same increment marginal, so the null pins the Brownian reference and
any real departure is a genuine coupling.
"""

from __future__ import annotations

import math
import statistics


def _pearson(x, y):
    if len(x) < 3:
        return 0.0
    mx, my = statistics.mean(x), statistics.mean(y)
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy) if sx * sy else 0.0


def within_leg_diffusion_exponent(legs_list) -> float:
    """Slope of log|dv| against log dt: the within-leg diffusion exponent H."""
    xs, ys = [], []
    for dt, dv in legs_list:
        if dt > 0 and abs(dv) > 0:
            xs.append(math.log(dt))
            ys.append(math.log(abs(dv)))
    if len(xs) < 10:
        return float("nan")
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else float("nan")


def cross_leg_couplings(legs_list) -> dict:
    """Cross-leg correlations of duration and size."""
    dt = [a for a, _ in legs_list]
    dv = [abs(b) for _, b in legs_list]
    return {
        "within_dt_dv": _pearson(dt, dv),
        "calm_then_move": _pearson(dt[:-1], dv[1:]),   # long wait -> big next move?
        "move_then_rest": _pearson(dv[:-1], dt[1:]),   # big move -> long next wait?
    }
