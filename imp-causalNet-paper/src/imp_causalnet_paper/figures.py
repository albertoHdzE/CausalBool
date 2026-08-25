"""Digitise the paper's own published figures back into cell grids.

Neither the preprint, the published paper, the supplement nor the authors' R
repository states the cellular-automaton parameters: tape width, number of steps,
initial condition, or how a mixed neighbourhood resolves.  The figures do.

The supplement embeds its figures as lossless, three-colour, pixel-aligned
images.  Recovering the cell grid from them turns the published pictures into
data, and the recovered data then determines every missing parameter -- and, as
it turns out, corrects the interaction model.

What this yields for Supplementary Fig. 2 (each panel 100 steps):

===========  =====  ======  ===================================================
panel        rules  width   initial condition
===========  =====  ======  ===================================================
a            54|50   ~216   two single live cells, 22 apart (pyramidal)
b            82|110  ~216   two single live cells, 22 apart (pyramidal)
c            60|110   100   random row spanning the width, split near cell 40
===========  =====  ======  ===================================================

Panel c is the configuration of the paper's main Fig. 2, and is shipped
pre-digitised as ``data/sup_fig2c_rules60_110.npy`` so the notebook runs without
Poppler or Pillow.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

__all__ = [
    "WHITE",
    "GREY",
    "RED",
    "load_sup_fig2c",
    "digitise_panel",
    "recover_local_rules",
    "mixed_transition_table",
    "determinism_by_radius",
]

WHITE, GREY, RED = 0, 1, 2

_DATA = Path(__file__).resolve().parents[2] / "data"


def load_sup_fig2c() -> np.ndarray:
    """The digitised Supplementary Fig. 2c as a ``(101, 100)`` array.

    Values are :data:`WHITE`, :data:`GREY` (rule 110, right) and :data:`RED`
    (rule 60, left).  Row 0 is the initial condition.
    """
    return np.load(_DATA / "sup_fig2c_rules60_110.npy")


# ---------------------------------------------------------------------------
# Digitisation
# ---------------------------------------------------------------------------


def digitise_panel(png_path, pitch_range=(8.5, 9.5)) -> np.ndarray:
    """Recover the cell grid from one supplementary-figure image.

    The pitch and offset of the pixel lattice are fitted from the positions of
    colour transitions rather than assumed, so a half-cell misalignment -- which
    would silently corrupt every neighbourhood -- cannot pass unnoticed.  The
    check that it has *not* happened is
    :func:`recover_local_rules`: a misaligned grid cannot yield a unique
    elementary rule.

    Requires Pillow; the pre-digitised array is available from
    :func:`load_sup_fig2c` without it.
    """
    from PIL import Image

    im = np.array(Image.open(png_path).convert("RGB")).astype(int)
    grey = np.abs(im - 127).sum(2) < 30
    red = np.abs(im - np.array([252, 13, 27])).sum(2) < 60
    lab = np.zeros(im.shape[:2], dtype=int)
    lab[grey] = GREY
    lab[red] = RED

    def _fit(transitions):
        best = None
        for p in np.arange(pitch_range[0], pitch_range[1], 0.002):
            for o in np.arange(0, p, 0.25):
                q = (transitions - o) / p
                score = float(np.abs(q - np.round(q)).mean())
                if best is None or score < best[0]:
                    best = (score, p, o)
        return best[1], best[2]

    def _transitions(arr):
        out = []
        for line in arr:
            out.extend((np.flatnonzero(np.diff(line) != 0) + 1).tolist())
        return np.array(out)

    px, ox = _fit(_transitions(lab))
    py, oy = _fit(_transitions(lab.T))

    ys, xs = np.nonzero(lab > 0)
    c0, r0 = int(round((xs.min() - ox) / px)), int(round((ys.min() - oy) / py))
    ncol = int(round((xs.max() + 1 - ox) / px)) - c0
    nrow = int(round((ys.max() + 1 - oy) / py)) - r0

    grid = np.zeros((nrow, ncol), dtype=int)
    for i in range(nrow):
        for j in range(ncol):
            grid[i, j] = lab[int(oy + (r0 + i + 0.5) * py), int(ox + (c0 + j + 0.5) * px)]
    return grid


# ---------------------------------------------------------------------------
# Reading the mechanism back out of the picture
# ---------------------------------------------------------------------------


def _signed(grid: np.ndarray) -> np.ndarray:
    """Red -> ``+1`` (left automaton), grey -> ``-1`` (right), white -> ``0``."""
    return np.where(grid == RED, 1, np.where(grid == GREY, -1, 0))


def recover_local_rules(grid: np.ndarray, cyclic: bool = True) -> dict[str, list[int]]:
    """Which elementary rules are consistent with each pure-colour region?

    This is the index-set consistency test of
    :mod:`~imp_causalnet_paper.causalbool_mirror` applied to the published
    picture.  A correct digitisation returns exactly one rule per colour; a
    misaligned one returns none.
    """
    S = _signed(grid)
    T, W = S.shape
    out: dict[str, list[int]] = {}
    for name, sign in (("red_left", 1), ("grey_right", -1)):
        constraints: dict[int, int] = {}
        ok = True
        for t in range(T - 1):
            for i in range(W):
                if cyclic:
                    nb = (S[t, (i - 1) % W], S[t, i], S[t, (i + 1) % W])
                else:
                    if i == 0 or i == W - 1:
                        continue
                    nb = (S[t, i - 1], S[t, i], S[t, i + 1])
                if not set(nb) <= {0, sign}:
                    continue
                idx = int(4 * abs(nb[0]) + 2 * abs(nb[1]) + abs(nb[2]))
                bit = 1 if S[t + 1, i] == sign else 0
                if constraints.setdefault(idx, bit) != bit:
                    ok = False
        out[name] = (
            [r for r in range(256) if all(((r >> i) & 1) == b for i, b in constraints.items())]
            if ok
            else []
        )
    return out


def mixed_transition_table(grid: np.ndarray, cyclic: bool = True) -> dict:
    """Observed outcome distribution for each of the twelve mixed neighbourhoods."""
    from collections import Counter, defaultdict

    S = _signed(grid)
    T, W = S.shape
    obs: dict[tuple[int, int, int], Counter] = defaultdict(Counter)
    for t in range(T - 1):
        for i in range(W):
            if cyclic:
                nb = (int(S[t, (i - 1) % W]), int(S[t, i]), int(S[t, (i + 1) % W]))
            else:
                if i == 0 or i == W - 1:
                    continue
                nb = (int(S[t, i - 1]), int(S[t, i]), int(S[t, i + 1]))
            if -1 in nb and 1 in nb:
                obs[nb][int(S[t + 1, i])] += 1
    return dict(obs)


def determinism_by_radius(grid: np.ndarray, radii=(1, 2, 3, 4, 5)) -> list[dict]:
    """Best achievable accuracy of a deterministic mixed rule at each radius.

    If the interaction were deterministic on a wider neighbourhood, accuracy
    would reach 1.0 at some radius *while the number of distinct neighbourhoods
    stayed well below the number of samples*.  If instead accuracy only climbs as
    the neighbourhood count approaches the sample count, the apparent
    determinism is memorisation and the process is genuinely stochastic.
    """
    from collections import Counter, defaultdict

    S = _signed(grid)
    T, W = S.shape
    rows = []
    for r in radii:
        obs: dict[tuple, Counter] = defaultdict(Counter)
        for t in range(T - 1):
            for i in range(W):
                idx = [(i + d) % W for d in range(-r, r + 1)]
                nb = tuple(int(S[t, j]) for j in idx)
                core = nb[r - 1 : r + 2]
                if not (-1 in core and 1 in core):
                    continue
                obs[nb][int(S[t + 1, i])] += 1
        n = sum(sum(c.values()) for c in obs.values())
        best = sum(max(c.values()) for c in obs.values())
        rows.append(
            {
                "radius": r,
                "distinct_neighbourhoods": len(obs),
                "samples": n,
                "best_accuracy": best / n if n else float("nan"),
            }
        )
    return rows
