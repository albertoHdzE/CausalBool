"""Finite-state statistics under the doppel-challenge contract.

Forward ``D_KL(p || q)`` uses the full N-bit alphabet.  Positive p mass on a
q-zero state is therefore infinite; conditional KL is a separate diagnostic.
"""
from __future__ import annotations

import math
from typing import Any, Literal

LossId = Literal["L_SINGLE_TARGET", "L_LINEAR", "L_ENTROPY"]


def _maps(rep: dict[str, Any]) -> tuple[dict[int, float], dict[int, int]]:
    support = list(rep.get("support", []))
    probs = list(rep.get("probs", []))
    if len(support) != len(probs):
        raise ValueError("support and probs lengths differ")
    if len(set(support)) != len(support):
        raise ValueError("support states must be unique")
    if any(not isinstance(state, int) for state in support):
        raise ValueError("support states must be integers")
    if any(not isinstance(probability, (int, float)) or probability < 0
           or not math.isfinite(float(probability)) for probability in probs):
        raise ValueError("probabilities must be finite and non-negative")
    if abs(sum(probs) - 1.0) > 1e-9:
        raise ValueError("probabilities must sum to one")
    return dict(zip(support, probs)), {s: i for i, s in enumerate(support)}


def conditional_kl(p_dict: dict[str, Any], q_dict: dict[str, Any]) -> float | None:
    """KL after separately conditioning p and q on their support intersection."""
    p, _ = _maps(p_dict)
    q, _ = _maps(q_dict)
    inter = sorted(set(p) & set(q))
    p_mass = sum(p[s] for s in inter)
    q_mass = sum(q[s] for s in inter)
    if not inter or p_mass <= 0 or q_mass <= 0:
        return None
    value = sum((p[s] / p_mass) * math.log((p[s] / p_mass) / (q[s] / q_mass))
                for s in inter if p[s] > 0 and q[s] > 0)
    return max(0.0, value)


def kl(p_dict: dict[str, Any], q_dict: dict[str, Any]) -> dict[str, Any]:
    """Return standard forward KL and explicit support diagnostics.

    The Python API returns ``math.inf`` for mathematical infinity.  When a
    result is persisted, callers should store a nullable numeric value plus
    the explicit status fields returned here (JSON has no infinity literal).
    """
    p, _ = _maps(p_dict)
    q, _ = _maps(q_dict)
    outside = sum(value for state, value in p.items() if value > 0 and q.get(state, 0.0) <= 0)
    inter = sorted(set(p) & set(q))
    common = {
        "support_disjoint": not inter,
        "support_intersection_size": len(inter),
        "p_mass_outside_q_support": outside,
        "conditional_D_KL_nats": conditional_kl(p_dict, q_dict),
        "p_intersection_mass": sum(p.get(state, 0.0) for state in inter),
        "q_intersection_mass": sum(q.get(state, 0.0) for state in inter),
    }
    if outside > 0:
        return {"D_KL_nats": math.inf, "infinite_kl": True,
                "divergence_status": "infinite", **common}
    value = 0.0
    for state, probability in p.items():
        if probability <= 0:
            continue
        q_probability = q.get(state, 0.0)
        if q_probability <= 0:
            return {"D_KL_nats": math.inf, "infinite_kl": True,
                    "divergence_status": "infinite", **common}
        value += probability * math.log(probability / q_probability)
    return {"D_KL_nats": max(0.0, value), "infinite_kl": False,
            "divergence_status": "finite", **common}


def total_variation(p_dict: dict[str, Any], q_dict: dict[str, Any]) -> float:
    p, _ = _maps(p_dict)
    q, _ = _maps(q_dict)
    return 0.5 * sum(abs(p.get(s, 0.0) - q.get(s, 0.0)) for s in set(p) | set(q))


def jensen_shannon(p_dict: dict[str, Any], q_dict: dict[str, Any]) -> float:
    p, _ = _maps(p_dict)
    q, _ = _maps(q_dict)
    value = 0.0
    for s in set(p) | set(q):
        a, b = p.get(s, 0.0), q.get(s, 0.0)
        m = 0.5 * (a + b)
        if a > 0:
            value += 0.5 * a * math.log(a / m)
        if b > 0:
            value += 0.5 * b * math.log(b / m)
    return value


def js_divergence(p_dict: dict[str, Any], q_dict: dict[str, Any]) -> float:
    """Named alias for Jensen--Shannon divergence in nats."""
    return jensen_shannon(p_dict, q_dict)


def cross_entropy(p_dict: dict[str, Any], q_dict: dict[str, Any]) -> float:
    """Cross-entropy H(p,q), including the q-zero/infinite edge case."""
    p, _ = _maps(p_dict)
    q, _ = _maps(q_dict)
    if any(probability > 0 and q.get(s, 0.0) <= 0 for s, probability in p.items()):
        return math.inf
    return sum(-probability * math.log(q[s]) for s, probability in p.items() if probability > 0)


def expected_loss(p_dict: dict[str, Any], loss_id: str,
                  loss_params: dict[str, Any],
                  q_dict: dict[str, Any] | None = None) -> float:
    """Expected declared loss under p."""
    support, probs = p_dict["support"], p_dict["probs"]
    if loss_id == "L_SINGLE_TARGET":
        targets = set(loss_params.get("targets", []))
        return sum(probability for state, probability in zip(support, probs) if state in targets)
    if loss_id == "L_LINEAR":
        weights = loss_params.get("weights", [])
        if len(weights) != int(p_dict.get("cols", max(support).bit_length() if support else 0)):
            raise ValueError("L_LINEAR weights must have one entry per network node")
        if any(not isinstance(weight, (int, float)) or not math.isfinite(float(weight))
               for weight in weights):
            raise ValueError("L_LINEAR weights must be finite numbers")
        return sum(probability * sum(weight for i, weight in enumerate(weights)
                   if weight and (state >> i) & 1)
                   for state, probability in zip(support, probs))
    if loss_id == "L_ENTROPY":
        if q_dict is None:
            raise ValueError("L_ENTROPY requires baseline q for cross-entropy")
        return cross_entropy(p_dict, q_dict)
    raise ValueError(f"unknown loss_id: {loss_id!r}")


def jaccard(p_dict: dict[str, Any], q_dict: dict[str, Any]) -> dict[str, Any]:
    p_set, q_set = set(p_dict["support"]), set(q_dict["support"])
    union, inter = p_set | q_set, p_set & q_set
    return {"support_jaccard": 1.0 - len(inter) / len(union) if union else 0.0,
            "support_size_A": len(p_set), "support_size_0": len(q_set),
            "support_intersection": sorted(inter)}


def support_distance(p_dict: dict[str, Any], q_dict: dict[str, Any]) -> dict[str, Any]:
    """Return the declared Jaccard support distance and its set diagnostics."""
    return jaccard(p_dict, q_dict)


def in_catalogue(query: dict[str, Any], catalogue: list[dict[str, Any]], tol: float = 0.0) -> bool:
    """Approximate open-set membership using support and union total variation."""
    for element in catalogue:
        if jaccard(query, element)["support_jaccard"] <= tol and total_variation(query, element) <= tol:
            return True
    return False


def constrained_optimum(rows: list[dict[str, Any]], baseline: dict[str, Any], C: float,
                        *, loss_id: str = "L_SINGLE_TARGET",
                        loss_params: dict[str, Any] | None = None,
                        exclude_identity: bool = True) -> dict[str, Any]:
    """Exact finite-catalogue optimum subject to standard KL <= C."""
    if C < 0:
        raise ValueError("C must be non-negative")
    params = loss_params or {}
    feasible = []
    for row in rows:
        if exclude_identity and (row.get("graph_distance") == 0 or
                                 str(row.get("perturbation_id", "")).endswith(":identity")):
            continue
        metric = kl(row["repertoire"], baseline)
        if not metric["infinite_kl"] and metric["D_KL_nats"] <= C + 1e-12:
            feasible.append((row, expected_loss(row["repertoire"], loss_id, params, baseline),
                             metric["D_KL_nats"]))
    best = max(feasible, key=lambda item: (item[1], -item[2]), default=None)
    return {"C": C, "n_candidates": len(rows), "n_feasible": len(feasible),
            "V_k_C": best[1] if best else None,
            "best_perturbation_id": best[0].get("perturbation_id") if best else None,
            "best_D_KL_nats": best[2] if best else None}


def kl_ball_upper_bound(q_dict: dict[str, Any], C: float, loss_id: str,
                        loss_params: dict[str, Any]) -> dict[str, float | None]:
    """Evaluate the exponential-family upper bound on a KL-ball payoff."""
    if C < 0:
        raise ValueError("C must be non-negative")
    states = list(q_dict["support"])
    q = dict(zip(states, q_dict["probs"]))
    if not states:
        return {"upper_bound": None, "lambda": None}
    losses = {s: expected_loss({"support": [s], "probs": [1.0], "cols": q_dict.get("cols")},
                               loss_id, loss_params, q_dict)
              for s in states}
    if C == 0:
        return {"upper_bound": sum(q[s] * losses[s] for s in states), "lambda": 0.0}

    max_loss = max(losses.values())
    max_states_mass = sum(q[state] for state, loss in losses.items()
                          if math.isclose(loss, max_loss, rel_tol=0.0, abs_tol=1e-15))
    # Once the KL ball can place all mass on the maximizing level set, the
    # relaxation has saturated at the unconstrained maximum.  This explicit
    # boundary avoids a misleading finite-grid approximation.
    saturation_cost = -math.log(max_states_mass) if max_states_mass > 0 else math.inf
    if C >= saturation_cost:
        return {"upper_bound": max_loss, "lambda": math.inf}
    if len({round(value, 15) for value in losses.values()}) == 1:
        return {"upper_bound": max_loss, "lambda": math.inf}

    def objective(lam: float) -> float:
        values = [math.log(q[s]) + lam * losses[s] for s in states if q[s] > 0]
        top = max(values)
        log_z = top + math.log(sum(math.exp(value - top) for value in values))
        return (C + log_z) / lam

    # The dual objective is convex in log-lambda but a simple logarithmic
    # search is sufficient and deterministic for this finite diagnostic.
    grid = [10 ** (-8 + 0.02 * i) for i in range(801)]
    best = min(grid, key=objective)
    value = min(max_loss, objective(best))
    return {"upper_bound": value, "lambda": best}
