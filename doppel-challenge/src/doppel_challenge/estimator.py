"""Approximate restart/trajectory estimation of the long-run repertoire.

The exact observable averages the phase-uniform distribution on the attractor
reached by every initial state.  A restart estimator samples initial states,
follows each deterministic trajectory until a cycle is detected, and averages
the phase-uniform cycle distributions.  It never enumerates the ``2**N``
state space and is therefore suitable for exploratory large-network pilots.

This module deliberately does not expose sampled results as exact results.
The returned record carries the approximation contract, convergence
diagnostics, uncertainty intervals, resource measurements, and an explicit
``accepted_validation`` flag (false until a benchmark gate accepts the
estimator).
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import resource
import sys
import time
import tracemalloc
from collections import defaultdict
from typing import Any, Iterable

from .adapters import Network, apply_gate, input_vector, step
from .execution import source_provenance
from .records import make_envelope, seal


OBSERVABLE = "basin_weighted_attractor_repertoire"
APPROXIMATION = "restart_trajectory_sampling"
CONVERGENCE_POLICY = "cycle_detection_with_finite_horizon_tail_fallback"
UNCERTAINTY_METHOD = "hoeffding_restart_mean"
TAIL_OBSERVATION_LIMIT = 256

try:
    import psutil
except ImportError:  # pragma: no cover - exercised only in minimal installs
    psutil = None


def _current_rss_bytes() -> int | None:
    """Return current resident memory when psutil is available."""
    if psutil is None:
        return None
    return int(psutil.Process().memory_info().rss)


def _process_max_rss_bytes() -> int:
    """Return the process high-water RSS with macOS/Linux normalization."""
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    # macOS reports bytes; Linux and the BSDs traditionally report KiB.
    return value if sys.platform == "darwin" else value * 1024


def _make_successor(net: Network):
    """Compile a network update into integer bit operations.

    The root ``step`` implementation is the reference path, but rebuilding an
    N-element input list for every transition dominates dense large-N pilots.
    Common gates are therefore compiled to masks while unusual configurations
    deliberately fall back to the reference gate semantics.
    """
    compiled = []
    for node, gate in enumerate(net.gates):
        sources = tuple(net.connected_inputs(node))
        mask = sum(1 << source for source in sources)
        params = net.params[node] or {}
        arity = len(sources)

        def reference(state: int, *, _gate=gate, _sources=sources, _params=params) -> int:
            inputs = [(state >> source) & 1 for source in _sources]
            return int(apply_gate(_gate, inputs, _params)) & 1

        if gate == "TRUE":
            compiled.append(lambda state: 1)
        elif gate == "FALSE":
            compiled.append(lambda state: 0)
        elif gate == "AND":
            compiled.append(lambda state, _mask=mask: int((state & _mask) == _mask))
        elif gate == "OR":
            compiled.append(lambda state, _mask=mask: int((state & _mask) != 0))
        elif gate == "XOR":
            compiled.append(lambda state, _mask=mask: (state & _mask).bit_count() & 1)
        elif gate == "NAND":
            compiled.append(lambda state, _mask=mask: int((state & _mask) != _mask))
        elif gate == "NOR":
            compiled.append(lambda state, _mask=mask: int((state & _mask) == 0))
        elif gate == "XNOR":
            compiled.append(lambda state, _mask=mask: 1 - ((state & _mask).bit_count() & 1))
        elif gate == "NOT" and arity == 1:
            source = sources[0]
            compiled.append(lambda state, _source=source: 1 - ((state >> _source) & 1))
        elif gate in {"IMPLIES", "NIMPLIES"} and arity == 2:
            left, right = sources
            if gate == "IMPLIES":
                compiled.append(lambda state, _a=left, _b=right:
                                int(((state >> _a) & 1) == 0 or ((state >> _b) & 1) == 1))
            else:
                compiled.append(lambda state, _a=left, _b=right:
                                int(((state >> _a) & 1) == 1 and ((state >> _b) & 1) == 0))
        elif gate == "MAJORITY":
            policy = params.get("tiePolicy", "strict")
            threshold = -(-arity // 2) if policy == "atOrAbove" else arity // 2 + 1
            compiled.append(lambda state, _mask=mask, _threshold=threshold:
                            int((state & _mask).bit_count() >= _threshold))
        elif gate == "KOFN" and isinstance(params.get("k", 1), int):
            threshold = params.get("k", 1)
            if params.get("strict", False):
                compiled.append(lambda state, _mask=mask, _threshold=threshold:
                                int((state & _mask).bit_count() > _threshold))
            else:
                compiled.append(lambda state, _mask=mask, _threshold=threshold:
                                int((state & _mask).bit_count() >= _threshold))
        elif gate == "CANALISING" and arity > 0:
            index = params.get("canalisingIndex", 0)
            value = params.get("canalisingValue", 1)
            output = params.get("canalisedOutput", 0)
            if isinstance(index, int) and 0 <= index < arity:
                source = sources[index]
                compiled.append(lambda state, _source=source, _value=value,
                                _output=output, _mask=mask:
                                int(_output if ((state >> _source) & 1) == _value
                                    else bool(state & _mask)))
            else:
                compiled.append(reference)
        elif gate == "REGULATORY" and isinstance(params.get("activators"), (list, tuple)):
            activators = set(params["activators"])
            if all(isinstance(index, int) and 0 <= index < arity for index in activators):
                activator_mask = sum(1 << sources[index] for index in activators)
                inhibitor_mask = mask & ~activator_mask
                compiled.append(lambda state, _a=activator_mask, _i=inhibitor_mask:
                                int((state & _a) == _a and (state & _i) == 0))
            else:
                compiled.append(reference)
        elif gate == "LUT" and isinstance(params.get("table"), (list, tuple)):
            table = params["table"]

            def lut(state: int, _table=table, _sources=sources) -> int:
                index = sum(((state >> source) & 1) << position
                             for position, source in enumerate(_sources))
                return int(_table[index]) & 1

            compiled.append(lut)
        else:
            compiled.append(reference)

    def successor(state: int) -> int:
        next_state = 0
        for node, output in enumerate(compiled):
            next_state |= output(state) << node
        return next_state

    return successor


def _successor(net: Network, state: int) -> int:
    """Calculate one successor using the reference adapter path."""
    bits = step(net, input_vector(state, net.n))
    return sum((int(bit) & 1) << index for index, bit in enumerate(bits))


def _cycle_from_restart(
    successor,
    start: int,
    max_steps: int,
) -> tuple[tuple[int, ...] | None, int, str, tuple[int, ...]]:
    """Return ``(cycle, transitions, status, path)`` for one restart.

    ``max_steps`` bounds the number of successor evaluations.  The successor
    after the final evaluation is checked as well, so a fixed point converges
    with a budget of one step.
    """
    seen: dict[int, int] = {}
    path: list[int] = []
    state = start
    transitions = 0
    while state not in seen and transitions < max_steps:
        seen[state] = len(path)
        path.append(state)
        state = successor(state)
        transitions += 1
    if state in seen:
        return tuple(path[seen[state]:]), transitions, "cycle_detected", tuple(path)
    return None, transitions, "max_steps_reached", tuple(path)


def _tail_stability(first: tuple[int, ...], second: tuple[int, ...]) -> float:
    """Total variation between two empirical trajectory-window measures."""
    if not first or not second:
        return 1.0
    left: dict[int, int] = defaultdict(int)
    right: dict[int, int] = defaultdict(int)
    for state in first:
        left[state] += 1
    for state in second:
        right[state] += 1
    support = set(left) | set(right)
    return 0.5 * sum(abs(left.get(state, 0) / len(first) -
                        right.get(state, 0) / len(second)) for state in support)


def _normal_interval(mean: float, standard_error: float, confidence: float) -> tuple[float, float]:
    """A normal interval used as a descriptive companion to the bound."""
    z_by_confidence = {0.90: 1.6448536269514722, 0.95: 1.959963984540054,
                       0.99: 2.5758293035489004}
    z = z_by_confidence.get(round(confidence, 2), 1.959963984540054)
    return max(0.0, mean - z * standard_error), min(1.0, mean + z * standard_error)


def _config_id(net: Network, parameters: dict[str, Any]) -> str:
    payload = {"N": net.n, "A": net.C, "gates": net.gates,
               "params": net.params, "estimator_parameters": parameters}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:20]


def estimate_repertoire(
    net: Network,
    samples: int,
    max_steps: int,
    seed: int,
    *,
    confidence: float = 0.95,
    initial_states: Iterable[int] | None = None,
    tail_fallback: bool = True,
    tail_observation_limit: int = TAIL_OBSERVATION_LIMIT,
) -> dict[str, Any]:
    """Estimate the declared repertoire with random restarts.

    Parameters are intentionally explicit: ``samples``, ``max_steps``, and
    ``seed`` are part of the scientific record.  If a trajectory does not
    close a cycle within ``max_steps``, the default tail fallback includes a
    finite-horizon post-burn-in window in the normalized estimate and records
    the truncation diagnostics.  A nonzero truncation rate makes the estimator
    computationally incomplete; callers should not use that result as a
    validated scaling result.

    If a cycle is not found within the budget, the default finite-horizon
    fallback averages a thinned post-burn-in trajectory window.  That window
    is included in the returned distribution (rather than being silently
    discarded), but the result remains computationally incomplete and cannot
    pass the exact-cycle convergence gate.  The per-state uncertainty interval
    uses Hoeffding's distribution-free radius for bounded restart
    contributions.  Standard errors and normal intervals are also included as
    descriptive diagnostics.
    """
    if not isinstance(net, Network):
        raise TypeError("net must be a Network")
    if not isinstance(samples, int) or samples <= 0:
        raise ValueError("samples must be a positive integer")
    if not isinstance(max_steps, int) or max_steps <= 0:
        raise ValueError("max_steps must be a positive integer")
    if not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie strictly between 0 and 1")
    if not isinstance(tail_fallback, bool):
        raise TypeError("tail_fallback must be a boolean")
    if not isinstance(tail_observation_limit, int) or tail_observation_limit <= 0:
        raise ValueError("tail_observation_limit must be a positive integer")

    parameters = {
        "samples": samples,
        "max_steps": max_steps,
        "seed": seed,
        "convergence_policy": CONVERGENCE_POLICY,
        "uncertainty_method": UNCERTAINTY_METHOD,
        "confidence_level": confidence,
        "tail_fallback": tail_fallback,
        "tail_observation_limit": tail_observation_limit,
    }
    started = time.perf_counter()
    rss_before = _current_rss_bytes()
    tracing_before = tracemalloc.is_tracing()
    if not tracing_before:
        tracemalloc.start()
    memory_before, _ = tracemalloc.get_traced_memory()
    rng = random.Random(seed)
    supplied_states = iter(initial_states) if initial_states is not None else None
    # Sparse online moments avoid retaining one dictionary per restart.  A
    # missing state contributes zero, so sums over nonzero cycle members are
    # sufficient for the exact sample mean and variance.
    state_sums: dict[int, float] = defaultdict(float)
    state_sumsq: dict[int, float] = defaultdict(float)
    cycle_counts: dict[tuple[int, ...], int] = defaultdict(int)
    transition_lengths: list[int] = []
    truncated = 0
    invalid_starts = 0
    tail_fallback_samples = 0
    tail_unstable_samples = 0
    tail_stability_values: list[float] = []

    successor = _make_successor(net)
    for _ in range(samples):
        start = next(supplied_states) if supplied_states is not None else rng.randrange(1 << net.n)
        if not isinstance(start, int) or not 0 <= start < (1 << net.n):
            invalid_starts += 1
            continue
        cycle, transitions, _status, path = _cycle_from_restart(successor, start, max_steps)
        transition_lengths.append(transitions)
        if cycle is None:
            truncated += 1
            if not tail_fallback:
                continue
            burn_in = len(path) // 2
            tail = path[burn_in:]
            midpoint = len(tail) // 2
            stability = _tail_stability(tail[:midpoint], tail[midpoint:])
            tail_stability_values.append(stability)
            if stability > 0.05:
                tail_unstable_samples += 1
            stride = max(1, math.ceil(len(tail) / tail_observation_limit))
            contribution_states = tail[::stride]
            tail_fallback_samples += 1
        else:
            cycle_counts[tuple(sorted(cycle))] += 1
            contribution_states = cycle
        contribution = 1.0 / len(contribution_states)
        contribution_squared = contribution * contribution
        for state in contribution_states:
            state_sums[state] += contribution
            state_sumsq[state] += contribution_squared

    converged = samples - truncated - invalid_starts
    estimated_samples = converged + tail_fallback_samples
    support = sorted(state_sums)
    means: dict[int, float] = {}
    standard_errors: dict[str, float] = {}
    normal_intervals: dict[str, list[float]] = {}
    for state in support:
        mean = state_sums[state] / estimated_samples
        means[state] = mean
        variance = ((state_sumsq[state] - estimated_samples * mean * mean) /
                    (estimated_samples - 1) if estimated_samples > 1 else 0.0)
        variance = max(0.0, variance)
        standard_error = math.sqrt(variance / estimated_samples) if estimated_samples else 0.0
        standard_errors[str(state)] = standard_error
        normal_intervals[str(state)] = list(_normal_interval(mean, standard_error, confidence))

    # A bounded-mean interval gives a conservative, distribution-free
    # diagnostic.  It remains available even for a single successful restart.
    alpha = 1.0 - confidence
    radius = (math.sqrt(math.log(2.0 / alpha) / (2.0 * estimated_samples))
              if estimated_samples else 1.0)
    confidence_intervals = {
        str(state): [max(0.0, means[state] - radius), min(1.0, means[state] + radius)]
        for state in support
    }
    runtime_seconds = time.perf_counter() - started
    rss_after = _current_rss_bytes()
    process_max_rss = _process_max_rss_bytes()
    _, peak_memory = tracemalloc.get_traced_memory()
    if not tracing_before:
        tracemalloc.stop()

    provenance = source_provenance()
    provenance["exact_state_space"] = False
    record = make_envelope(
        "approximate_repertoire",
        config_id=_config_id(net, parameters),
        sweep_id=None,
    )
    record.update({
        "N": net.n,
        "rows": 1 << net.n,
        "cols": net.n,
        "matrix_lsb_first": True,
        "support": support,
        "counts": None,
        "probability_denominator": None,
        "probs": [means[state] for state in support],
        "observable": OBSERVABLE,
        "approximation": APPROXIMATION,
        "estimator_parameters": parameters,
        "uncertainty": {
            "method": UNCERTAINTY_METHOD,
            "confidence_level": confidence,
            "effective_samples": estimated_samples,
            "standard_error": standard_errors,
            "confidence_intervals": confidence_intervals,
            "normal_intervals": normal_intervals,
            "hoeffding_radius": radius,
        },
        "convergence": {
            "policy": CONVERGENCE_POLICY,
            "requested_samples": samples,
            "converged_samples": converged,
            "estimated_samples": estimated_samples,
            "truncated_samples": truncated,
            "invalid_starts": invalid_starts,
            "truncated_fraction": truncated / samples,
            "tail_fallback_samples": tail_fallback_samples,
            "tail_unstable_samples": tail_unstable_samples,
            "tail_stability_tolerance": 0.05,
            "mean_tail_window_total_variation": (
                sum(tail_stability_values) / len(tail_stability_values)
                if tail_stability_values else None
            ),
            "max_tail_window_total_variation": (
                max(tail_stability_values) if tail_stability_values else None
            ),
            "mean_trajectory_steps": (sum(transition_lengths) / len(transition_lengths)
                                       if transition_lengths else None),
            "observed_cycle_count": len(cycle_counts),
            "observed_cycles": [list(cycle) for cycle in sorted(cycle_counts)],
        },
        "process_status": "normal_exit",
        "accepted_validation": False,
        "validation_scope": "approximate_computational_pilot",
        "provenance": provenance,
        "runtime_seconds": runtime_seconds,
        "peak_memory_bytes": max(0, peak_memory - memory_before),
        "resource_usage": {
            "method": "psutil_current_plus_resource_high_water" if psutil is not None
                      else "resource_ru_maxrss_high_water",
            "rss_before_bytes": rss_before,
            "rss_after_bytes": rss_after,
            "process_max_rss_bytes": process_max_rss,
        },
    })
    return seal(record)


__all__ = ["estimate_repertoire"]
