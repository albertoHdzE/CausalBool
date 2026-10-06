"""gap-ranking-v1-r1 -- recurrence-gap score and ranking of causal state groupings.

Thin run-local orchestration of corrected DESIGN.md §4 (Track G) under PROTOCOL.md §4.
Models, partitions and candidate IDs come from the adopted source revision
(``study``, abstraction-validation-v1-r1-source-r2); occurrence extraction and gaps come
from the isolated seqdecon owner (``token_occurrence_frames``, ``gaps``).  Block slicing
into tokens stays here, as the ticket requires.  Nothing here reads outcome labels.

Exact arithmetic throughout: a score is the pair (regular, eligible) of integers;
comparison uses ``fractions.Fraction``.  eligible == 0 is UNAVAILABLE, never zero.
"""
from __future__ import annotations

from fractions import Fraction

from seqdecon.operators import gaps, token_occurrence_frames

STEPS = 64
MIN_OCCURRENCES = 3
CONTROL_IDS = "F1 val, identity, constant"


# --------------------------------------------------------------------------- trajectories

def start_states(n: int) -> list[int]:
    """The six declared starting states, in declared order."""
    return [0, 1, 2 ** (n - 1), 2 ** n - 1,
            sum(2 ** i for i in range(0, n, 2)), sum(2 ** i for i in range(1, n, 2))]


def trajectory(F: list[int], x0: int, steps: int = STEPS) -> list[int]:
    """x_0 .. x_steps under the autonomous one-step table F."""
    xs = [x0]
    for _ in range(steps):
        xs.append(F[xs[-1]])
    return xs


def sample(xs: list[int], tau: int) -> list[int]:
    """States x_0, x_tau, ...; the returned list index is the sampled-frame index."""
    return xs[0:(len(xs) - 1) // tau * tau + 1:tau]


def block_tokens(states: list[int], a: int, ln: int) -> list[int]:
    """Token of block [a, a+ln): (x >> a) & (2**ln - 1), LSB-first."""
    if any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in states):
        raise ValueError("block_tokens requires nonnegative int states")
    mask = (1 << ln) - 1
    return [(x >> a) & mask for x in states]


# --------------------------------------------------------------------------- occurrence sets

def occurrence_records(sampled: list[list[int]], blocks: list[tuple[int, int]]) -> list[dict]:
    """One record per (trajectory, block, observed value); trajectories never joined."""
    recs = []
    for t, states in enumerate(sampled):
        for b, (a, ln) in enumerate(blocks):
            toks = block_tokens(states, a, ln)
            for v in sorted(set(toks)):
                frames = token_occurrence_frames(toks, v)
                g = gaps(frames)
                eligible = len(frames) >= MIN_OCCURRENCES
                recs.append({"traj": t, "block": b, "a": a, "len": ln, "value": v,
                             "frames": frames, "gaps": g, "eligible": eligible,
                             "regular": eligible and len(set(g)) == 1})
    return recs


def pooled_score(recs: list[dict]) -> dict:
    """Pool by counting eligible sets over all trajectories; no mean of fractions."""
    den = sum(1 for r in recs if r["eligible"])
    num = sum(1 for r in recs if r["regular"])
    return {"regular": num, "eligible": den, "available": den > 0}


def as_fraction(score: dict) -> Fraction | None:
    return Fraction(score["regular"], score["eligible"]) if score["available"] else None


# --------------------------------------------------------------------------- population and rank

def is_ranked(cand: dict) -> bool:
    """Every raw candidate except the 9 F1 val recodings and the 2 C controls."""
    if cand["family"] == "C":
        return False
    return not (cand["family"] == "F1" and cand["g"] == "val")


def candidate_score(cand: dict, wo_scores: dict) -> dict | None:
    """F1/F3/F4 inherit their first-level (w, o) score; F2 is UNAVAILABLE (None)."""
    if cand["family"] == "F2":
        return None
    return wo_scores[(cand["w"], cand["o"])]


def rank(cands: list[dict], wo_scores: dict) -> list[int]:
    """Available scores descending (exact), ties by ascending id; UNAVAILABLE last by id."""
    avail, unavail = [], []
    for c in cands:
        s = candidate_score(c, wo_scores)
        f = as_fraction(s) if s is not None else None
        (unavail if f is None else avail).append((f, c["id"]))
    avail.sort(key=lambda p: (-p[0], p[1]))
    unavail.sort(key=lambda p: p[1])
    return [cid for _, cid in avail] + [cid for _, cid in unavail]


def canonical(cands: list[dict]) -> list[int]:
    return sorted(c["id"] for c in cands)
