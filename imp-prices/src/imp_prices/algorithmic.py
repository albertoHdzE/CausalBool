"""BDM as the model term of an algorithmic two-part code (protocol 1b.3).

    L(model) = BDM(model encoded as a discrete array)
    L(data | model) = residual code, or negative log likelihood

This is the Kolmogorov structure function in the form the three sibling packages
use: algorithmic on the model side, while still paying for misfit, so that
neither an empty model nor an unconstrained one can win by construction. BDM
alone would answer "which object is more complex", not "which describes the data
better", and would be riggable by proposing a smaller model that predicts
nothing.

**The resolution caveat is enforced, not assumed.** imp-pathinfo established that
BDM can track object size rather than structure. :func:`resolution_check`
measures the separation between structured and random arrays at a given shape and
is called before any verdict; at 4×4 the separation is only about 3.5 standard
deviations of the random spread, at 8×8 about 18 and at 12×12 about 34. That is
why the object scored here is the whole network's connectivity matrix rather than
a single node's table.
"""

from __future__ import annotations

import warnings

import numpy as np

warnings.filterwarnings("ignore", message=".*pkg_resources.*")

from pybdm import BDM  # noqa: E402

_BDM2 = BDM(ndim=2)
_BDM1 = BDM(ndim=1)


def bdm_bits(array: np.ndarray) -> float:
    """BDM of a binary array, in bits.

    One and two dimensional arrays are dispatched to the matching CTM dataset.
    Anything non-binary raises rather than being silently coerced, because a
    coerced array would be measured but would not be the object intended.
    """
    a = np.asarray(array, dtype=int)
    u = np.unique(a)
    if not np.all(np.isin(u, (0, 1))):
        raise ValueError(f"BDM here is binary; got values {u[:8]}")
    if a.ndim == 1:
        return float(_BDM1.bdm(a))
    if a.ndim == 2:
        return float(_BDM2.bdm(a))
    raise ValueError(f"unsupported ndim {a.ndim}")


def resolution_check(shape: tuple[int, int], n_random: int = 200,
                     seed: int = 42) -> dict:
    """Can BDM separate structure from noise at this shape? (control 1b.4)

    Returns the separation in standard deviations of the random spread. A
    verdict drawn from a shape where this is small is not a verdict about
    structure; it is a verdict about size.
    """
    rng = np.random.default_rng(seed)
    n, m = shape
    identity = np.eye(n, m, dtype=int)
    constant = np.ones(shape, dtype=int)
    randoms = [rng.integers(0, 2, size=shape) for _ in range(n_random)]
    r = np.array([bdm_bits(x) for x in randoms])
    sep = (r.mean() - bdm_bits(identity)) / max(r.std(), 1e-12)
    return dict(shape=list(shape),
                constant=round(bdm_bits(constant), 3),
                identity=round(bdm_bits(identity), 3),
                random_mean=round(float(r.mean()), 3),
                random_sd=round(float(r.std()), 3),
                separation_sigma=round(float(sep), 2),
                usable=bool(sep > 5.0))


def two_part_algorithmic(structure: np.ndarray, table: np.ndarray,
                         data_bits: float) -> dict:
    """BDM(connectivity) + BDM(tables) + L(data | model)."""
    s = bdm_bits(structure)
    t = bdm_bits(table)
    return dict(structure_bdm=round(s, 3), table_bdm=round(t, 3),
                model_bits=round(s + t, 3), data_bits=round(data_bits, 3),
                total_bits=round(s + t + data_bits, 3))


def structure_axis(c_a: np.ndarray, c_b: np.ndarray, name_a: str,
                   name_b: str) -> dict:
    """BDM of two connectivity matrices of identical shape.

    This is the one comparison in which size cannot confound the instrument,
    because both matrices are n x n over the same node set by construction. Edge
    counts are reported alongside so that a difference in density is visible
    rather than being absorbed silently into the complexity number.
    """
    if c_a.shape != c_b.shape:
        raise ValueError(f"shapes differ: {c_a.shape} vs {c_b.shape}")
    return dict(shape=list(c_a.shape),
                **{f"bdm_{name_a}": round(bdm_bits(c_a), 3),
                   f"bdm_{name_b}": round(bdm_bits(c_b), 3),
                   f"edges_{name_a}": int(c_a.sum()),
                   f"edges_{name_b}": int(c_b.sum()),
                   "difference": round(bdm_bits(c_a) - bdm_bits(c_b), 3)})
