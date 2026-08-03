"""Elementary cellular automata and the paper's *interacting* (competing) CA model.

Sections 2.1-2.3 and Supplementary Information 4.1 of arXiv:1802.09904v8.

The interaction model is the one of Adams, Zenil, Reyes and Joosten (2015): two
elementary cellular automata occupy the same tape, each in its own colour, and a
third "global" rule dictates what happens in the twelve neighbourhoods where the
two colours meet.  The Sup. Inf. gives the enumeration verbatim::

    R[x_] := Thread[Rule[{{-1,1,0},{-1,0,1},{-1,1,1},{1,-1,1},{1,-1,0},
    {1,1,-1},{1,0,-1}, {0,1,-1},{0,-1,1}, {1,-1,-1},{-1,1,-1},
    {-1,-1,1}}, Flatten[Take[Tuples[{-1,0,1},12],{x,x}]]]];
    Code[n_] := BitXor[n, BitShiftRight[n]];
    RuleCode[n_] := IntegerDigits[Code[n], 2]

Every figure in the paper that involves interacting CA quotes interaction rule
number ``531441``.  That number is ``3**12``, the last word of the enumeration,
which maps *every* mixed neighbourhood to ``+1`` -- so one automaton would simply
consume the other at one cell per step.

Digitising the paper's own Supplementary Fig. 2c shows this is not what the
published figures do.  Their pure regions are 100% deterministic and recover
rules 60 and 110 uniquely out of 256, confirming the reading of the image; but
their mixed transitions are *not* deterministic at any neighbourhood radius.  The
published dynamics are stochastic, which is what the main text says in prose:

    "there is no correlation between the random values of c_{t+1}(x_j) and of
     c_{t'+1}(x_i) ... In particular the mixed neighbourhood <2,2,1> may
     sometimes yield a 0, sometimes a 1 and at yet other times a 2."

:func:`evolve_interacting` therefore defaults to ``interaction="stochastic"``.
The deterministic enumeration is kept and is still exercised by the tests, but it
does not describe the figures.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np

__all__ = [
    "MIXED_NEIGHBOURHOODS",
    "INTERACTION_RULE_PAPER",
    "interaction_rule",
    "code",
    "rule_code",
    "eca_rule_table",
    "evolve_eca",
    "InteractingCA",
    "evolve_interacting",
]

# The twelve neighbourhoods that contain both colours, in the Sup. Inf. order.
MIXED_NEIGHBOURHOODS: tuple[tuple[int, int, int], ...] = (
    (-1, 1, 0),
    (-1, 0, 1),
    (-1, 1, 1),
    (1, -1, 1),
    (1, -1, 0),
    (1, 1, -1),
    (1, 0, -1),
    (0, 1, -1),
    (0, -1, 1),
    (1, -1, -1),
    (-1, 1, -1),
    (-1, -1, 1),
)

#: The interaction rule number quoted throughout the paper (Figs. 1F, 2, 6, 7, 8).
#:
#: Note that ``R[531441]`` is a *deterministic* rule (see :func:`interaction_rule`),
#: but digitising the paper's own Supplementary Fig. 2c shows the published
#: dynamics are **not** deterministic in mixed neighbourhoods.  Use
#: ``interaction="stochastic"`` to reproduce the figures; see
#: :func:`evolve_interacting`.
INTERACTION_RULE_PAPER = 531441

#: The published dynamics: a mixed neighbourhood resolves at random.
STOCHASTIC = "stochastic"


def interaction_rule(x: int = INTERACTION_RULE_PAPER) -> dict[tuple[int, int, int], int]:
    """``R[x]``: the map from mixed neighbourhoods to the surviving colour.

    ``Tuples[{-1,0,1}, 12]`` is the lexicographic enumeration of the 3**12 =
    531441 twelve-letter words over ``{-1,0,1}``; ``Take[..., {x, x}]`` selects
    the ``x``-th (1-based).  Word ``x`` is therefore the base-3 expansion of
    ``x - 1`` with the digit map ``0 -> -1, 1 -> 0, 2 -> +1``, most significant
    digit first.

    For the paper's ``x = 531441 = 3**12`` every digit is ``2``, so *every*
    mixed neighbourhood resolves to ``+1``: the right-hand automaton always
    survives contact.  This is why the paper reports "rule 110 prevailing over
    255" in Fig. 1F.
    """
    n_mixed = len(MIXED_NEIGHBOURHOODS)
    if not 1 <= x <= 3**n_mixed:
        raise ValueError(f"interaction rule index must lie in [1, 3**12]; got {x}")
    digits: list[int] = []
    value = x - 1
    for _ in range(n_mixed):
        digits.append(value % 3)
        value //= 3
    digits.reverse()  # Tuples varies the *last* position fastest
    alphabet = (-1, 0, 1)
    return {nb: alphabet[d] for nb, d in zip(MIXED_NEIGHBOURHOODS, digits)}


def code(n: int) -> int:
    """``Code[n_] := BitXor[n, BitShiftRight[n]]`` -- the binary-reflected Gray code."""
    return n ^ (n >> 1)


def rule_code(n: int) -> list[int]:
    """``RuleCode[n_] := IntegerDigits[Code[n], 2]``."""
    c = code(n)
    return [int(b) for b in bin(c)[2:]] if c else [0]


# ---------------------------------------------------------------------------
# Plain elementary cellular automata
# ---------------------------------------------------------------------------


def eca_rule_table(rule: int) -> np.ndarray:
    """Wolfram-code lookup table indexed by ``4*left + 2*centre + right``."""
    if not 0 <= rule <= 255:
        raise ValueError("an elementary CA rule number must lie in [0, 255]")
    return np.array([(rule >> i) & 1 for i in range(8)], dtype=int)


def evolve_eca(
    rule: int,
    initial: Iterable[int],
    steps: int,
    cyclic: bool = True,
) -> np.ndarray:
    """Space-time diagram of an ECA, ``steps + 1`` rows including the initial one.

    Cyclic boundaries match Mathematica's ``CellularAutomaton`` default.
    """
    table = eca_rule_table(rule)
    row = np.asarray(list(initial), dtype=int)
    out = [row.copy()]
    for _ in range(steps):
        if cyclic:
            left, right = np.roll(row, 1), np.roll(row, -1)
        else:
            left = np.concatenate([[0], row[:-1]])
            right = np.concatenate([row[1:], [0]])
        row = table[4 * left + 2 * row + right]
        out.append(row.copy())
    return np.array(out, dtype=int)


# ---------------------------------------------------------------------------
# Two interacting elementary cellular automata
# ---------------------------------------------------------------------------


class InteractingCA:
    """Result of running two ECA against each other on a shared tape.

    Attributes
    ----------
    signed:
        ``(steps + 1, width)`` array over ``{-1, 0, +1}``.  ``-1`` is a live
        cell of the left automaton (the paper's auxiliary "grey"), ``+1`` a live
        cell of the right automaton ("black"), ``0`` is white.
    observed:
        ``abs(signed)``.  This is all an outside observer gets: a binary image in
        which the two mechanisms are, by construction, not colour-coded.  Every
        deconvolution in this replication consumes *only* this array.
    owner:
        Ground truth, ``-1`` / ``+1`` per pixel, recording which automaton was
        responsible for the cell.  Used exclusively for scoring, never as input.
    """

    def __init__(self, signed: np.ndarray, owner: np.ndarray, meta: dict):
        self.signed = signed
        self.owner = owner
        self.meta = meta

    @property
    def observed(self) -> np.ndarray:
        return np.abs(self.signed).astype(int)

    @property
    def shape(self) -> tuple[int, int]:
        return self.signed.shape

    def __repr__(self) -> str:  # pragma: no cover - display helper
        m = self.meta
        return (
            f"InteractingCA(rules={m['rule_left']} vs {m['rule_right']}, "
            f"interaction={m['interaction']}, shape={self.shape})"
        )


def evolve_interacting(
    rule_left: int,
    rule_right: int,
    width: int = 100,
    steps: int = 100,
    interaction: int | str = STOCHASTIC,
    seed: int | None = 0,
    cyclic: bool = True,
    initial: np.ndarray | str | None = None,
    seed_gap: int = 22,
) -> InteractingCA:
    """Run ``rule_left`` against ``rule_right`` on a shared tape.

    Resolution order for a neighbourhood ``(l, c, r)``:

    1. both colours present  -> the interaction;
    2. only the left colour  -> ``rule_left`` applied to ``abs`` of the cells;
    3. only the right colour -> ``rule_right``;
    4. all white             -> stays white.  The published description leaves
       this open, but Fig. 1F settles it empirically: it runs rule 255, whose
       ``000`` bit is set, and yet produces a light cone rather than a filled
       tape.  Digitising that figure gives 2302 all-white neighbourhoods and
       2302 white successors, so the quiescent state is absorbing and overrides
       the automaton's own rule.

    Parameters
    ----------
    interaction:
        ``"stochastic"`` (default) reproduces the published figures: a mixed
        neighbourhood yields ``-1``, ``0`` or ``+1`` drawn uniformly at random
        and independently each time.  This is what the paper's main text
        describes -- "the mixed neighbourhood <2,2,1> may sometimes yield a 0,
        sometimes a 1 and at yet other times a 2" -- and what digitising
        Supplementary Fig. 2c confirms: the pure regions of the published image
        are 100% deterministic and recover rules 60 and 110 uniquely, while the
        mixed transitions are not deterministic at any neighbourhood radius.

        An integer instead selects the deterministic rule ``R[x]`` of
        :func:`interaction_rule`.  ``R[531441]`` maps every mixed neighbourhood
        to ``+1``, so one automaton simply consumes the other; that produces a
        clean diagonal front and **not** the interpenetration seen in the paper.
    initial:
        ``"random"`` (default) gives a random row spanning the width, the
        condition used for Fig. 2 and Sup. Fig. 2c.  ``"points"`` gives a single
        live cell per automaton, ``seed_gap`` cells apart, which is the
        pyramidal condition of Sup. Figs. 2a-b.  An array may be passed instead.

    Notes
    -----
    Geometry recovered by digitising the published figures:
    Sup. Fig. 2c (rules 60 | 110) is 100 cells wide over 100 steps from a random
    spanning row; Sup. Figs. 2a-b are ~216 cells wide over 100 steps from two
    single seeds 22 cells apart.
    """
    rng = np.random.default_rng(seed)
    table_l = eca_rule_table(rule_left)
    table_r = eca_rule_table(rule_right)
    stochastic = interaction == STOCHASTIC
    mixed = None if stochastic else interaction_rule(int(interaction))

    half = width // 2
    if initial is None or (isinstance(initial, str) and initial == "random"):
        row = np.zeros(width, dtype=int)
        row[:half] = -rng.integers(0, 2, half)
        row[half:] = rng.integers(0, 2, width - half)
    elif isinstance(initial, str) and initial == "points":
        row = np.zeros(width, dtype=int)
        row[half - seed_gap // 2] = -1
        row[half + seed_gap - seed_gap // 2] = 1
    else:
        row = np.asarray(initial, dtype=int).copy()

    owner_row = np.where(np.arange(width) < half, -1, 1)

    signed_rows = [row.copy()]
    owner_rows = [owner_row.copy()]

    for _ in range(steps):
        if cyclic:
            l, r = np.roll(row, 1), np.roll(row, -1)
        else:
            l = np.concatenate([[0], row[:-1]])
            r = np.concatenate([row[1:], [0]])

        has_neg = (l == -1) | (row == -1) | (r == -1)
        has_pos = (l == 1) | (row == 1) | (r == 1)
        is_mixed = has_neg & has_pos

        idx = 4 * np.abs(l) + 2 * np.abs(row) + np.abs(r)
        out_l = -table_l[idx]  # left automaton emits its own colour
        out_r = table_r[idx]

        # An all-white neighbourhood stays white -- see the docstring; this is
        # read off Fig. 1F rather than assumed.
        all_white = ~has_neg & ~has_pos
        new = np.where(has_neg & ~has_pos, out_l, out_r)
        new = np.where(all_white, 0, new)

        idx_mixed = np.flatnonzero(is_mixed)
        if idx_mixed.size:
            if stochastic:
                new[idx_mixed] = rng.integers(-1, 2, idx_mixed.size)
            else:
                for k in idx_mixed:
                    new[k] = mixed[(int(l[k]), int(row[k]), int(r[k]))]

        # Territory update: a live cell owns itself; a dead cell keeps the
        # territory of the nearest live neighbour, else its previous label.
        new_owner = np.where(new != 0, np.sign(new), 0)
        fallback = np.where(row != 0, np.sign(row), 0)
        fallback = np.where(fallback != 0, fallback, np.where(l != 0, np.sign(l), 0))
        fallback = np.where(fallback != 0, fallback, np.where(r != 0, np.sign(r), 0))
        fallback = np.where(fallback != 0, fallback, owner_row)
        new_owner = np.where(new_owner != 0, new_owner, fallback)

        row, owner_row = new.astype(int), new_owner.astype(int)
        signed_rows.append(row.copy())
        owner_rows.append(owner_row.copy())

    meta = dict(
        rule_left=rule_left,
        rule_right=rule_right,
        interaction=interaction,
        stochastic=stochastic,
        width=width,
        steps=steps,
        seed=seed,
        cyclic=cyclic,
    )
    return InteractingCA(np.array(signed_rows), np.array(owner_rows), meta)
