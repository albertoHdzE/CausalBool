from __future__ import annotations

import csv
import json
import math
import random
import statistics
import time
import tracemalloc
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

SIZES = [30, 60, 80, 200]
REPLICATES = 5
LOCAL_WINDOW = 4
MAX_INDEGREE = 4
ROW_THROUGHPUTS = [10**6, 10**8, 10**9]

GATE_FAMILIES = [
    "AND",
    "OR",
    "XOR",
    "NAND",
    "NOR",
    "XNOR",
    "NOT",
    "IMPLIES",
    "NIMPLIES",
    "MAJORITY",
    "KOFN",
]


def gate_output(gate: str, inputs: list[int], params: dict[str, int] | None = None) -> int:
    params = params or {}
    total = sum(inputs)
    if gate == "AND":
        return int(total == len(inputs))
    if gate == "OR":
        return int(total >= 1)
    if gate == "XOR":
        return total % 2
    if gate == "NAND":
        return 1 - int(total == len(inputs))
    if gate == "NOR":
        return int(total == 0)
    if gate == "XNOR":
        return 1 - (total % 2)
    if gate == "NOT":
        return 1 - inputs[0]
    if gate == "IMPLIES":
        return int((1 - inputs[0]) or inputs[1])
    if gate == "NIMPLIES":
        return int(inputs[0] and (1 - inputs[1]))
    if gate == "MAJORITY":
        return int(total >= (len(inputs) // 2 + 1))
    if gate == "KOFN":
        return int(total >= params["k"])
    raise ValueError(f"Unsupported gate: {gate}")


def compatible_gate_choices(degree: int) -> list[str]:
    gates: list[str] = []
    for gate in GATE_FAMILIES:
        if gate == "NOT" and degree != 1:
            continue
        if gate in {"IMPLIES", "NIMPLIES"} and degree != 2:
            continue
        if gate in {"AND", "OR", "XOR", "NAND", "NOR", "XNOR", "MAJORITY", "KOFN"} and degree < 1:
            continue
        gates.append(gate)
    return gates


def make_ring_local_network(n: int, seed: int) -> dict[str, object]:
    rng = random.Random(seed)
    inputs_by_node: list[list[int]] = []
    gates: list[str] = []
    params_by_node: list[dict[str, int]] = []

    for node in range(1, n + 1):
        candidate_inputs = [((node - offset - 1) % n) + 1 for offset in range(1, LOCAL_WINDOW + 1)]
        degree = rng.randint(1, min(MAX_INDEGREE, len(candidate_inputs)))
        gate = rng.choice(compatible_gate_choices(degree))

        if gate == "NOT":
            degree = 1
        elif gate in {"IMPLIES", "NIMPLIES"}:
            degree = 2

        coords = sorted(rng.sample(candidate_inputs, degree))
        params: dict[str, int] = {}
        if gate == "KOFN":
            params["k"] = rng.randint(1, degree)

        inputs_by_node.append(coords)
        gates.append(gate)
        params_by_node.append(params)

    return {
        "n": n,
        "seed": seed,
        "inputs_by_node": inputs_by_node,
        "gates": gates,
        "params_by_node": params_by_node,
    }


def network_update(state: list[int], network: dict[str, object]) -> list[int]:
    inputs_by_node = network["inputs_by_node"]
    gates = network["gates"]
    params_by_node = network["params_by_node"]
    outputs: list[int] = []
    for coords, gate, params in zip(inputs_by_node, gates, params_by_node):
        local_inputs = [state[c - 1] for c in coords]
        outputs.append(gate_output(gate, local_inputs, params))
    return outputs


def local_assignments(
    coords: list[int], gate: str, target: int, params: dict[str, int]
) -> list[dict[int, int]]:
    assignments: list[dict[int, int]] = []
    arity = len(coords)
    for mask in range(1 << arity):
        bits = [(mask >> i) & 1 for i in range(arity)]
        if gate_output(gate, bits, params) == target:
            assignments.append({coords[i]: bits[i] for i in range(arity)})
    return assignments


def merge_assignments(
    left: dict[int, int], right: dict[int, int]
) -> dict[int, int] | None:
    merged = dict(left)
    for key, value in right.items():
        if key in merged and merged[key] != value:
            return None
        merged[key] = value
    return merged


def canonicalize(partials: list[dict[int, int]]) -> list[dict[int, int]]:
    seen: dict[tuple[tuple[int, int], ...], dict[int, int]] = {}
    for partial in partials:
        key = tuple(sorted(partial.items()))
        seen[key] = partial
    return list(seen.values())


def exact_query_representation(
    network: dict[str, object],
    query_nodes: list[int],
    target_bits: list[int],
) -> dict[str, object]:
    inputs_by_node = network["inputs_by_node"]
    gates = network["gates"]
    params_by_node = network["params_by_node"]
    partials: list[dict[int, int]] = [dict()]
    support_union: set[int] = set()

    for node, bit in zip(query_nodes, target_bits):
        coords = inputs_by_node[node - 1]
        support_union.update(coords)
        options = local_assignments(coords, gates[node - 1], bit, params_by_node[node - 1])
        next_partials: list[dict[int, int]] = []
        for partial in partials:
            for option in options:
                merged = merge_assignments(partial, option)
                if merged is not None:
                    next_partials.append(merged)
        partials = canonicalize(next_partials)

    support_union_sorted = sorted(support_union)
    support_rows = []
    for partial in partials:
        support_rows.append([partial.get(coord, 0) for coord in support_union_sorted])

    free_coordinates = network["n"] - len(support_union_sorted)
    total_global_states = len(partials) * (1 << free_coordinates)

    return {
        "query_nodes": query_nodes,
        "target_bits": target_bits,
        "support_union": support_union_sorted,
        "support_size": len(support_union_sorted),
        "free_coordinates": free_coordinates,
        "support_assignments_count": len(partials),
        "support_assignments_sample": support_rows[:8],
        "total_global_states": total_global_states,
        "reduction_factor": 1 << free_coordinates,
        "overlap_multiplicity": sum(len(inputs_by_node[node - 1]) for node in query_nodes) - len(support_union_sorted),
    }


def measure_exact_method(
    network: dict[str, object],
    query_nodes: list[int],
    target_bits: list[int],
) -> dict[str, object]:
    tracemalloc.start()
    start = time.perf_counter()
    result = exact_query_representation(network, query_nodes, target_bits)
    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result["wall_time_seconds"] = elapsed
    result["peak_memory_bytes"] = peak
    return result


def choose_query_nodes(n: int, size: int, offset: int) -> list[int]:
    start = offset % n
    return [((start + idx) % n) + 1 for idx in range(size)]


def naive_resource_envelope(n: int) -> dict[str, object]:
    rows = 1 << n
    full_bits = n * rows
    full_bytes = math.ceil(full_bits / 8)
    return {
        "rows": rows,
        "full_output_bits": full_bits,
        "full_output_bytes": full_bytes,
        "throughput_seconds": {str(rate): rows / rate for rate in ROW_THROUGHPUTS},
    }


def sci(value: int | float) -> str:
    if value == 0:
        return "0"
    if isinstance(value, int):
        return f"{value:.3e}"
    return f"{value:.3e}"


def human_bytes(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    value = float(num_bytes)
    unit_idx = 0
    while value >= 1024.0 and unit_idx < len(units) - 1:
        value /= 1024.0
        unit_idx += 1
    if unit_idx == len(units) - 1 and value >= 1024.0:
        return f"{num_bytes:.3e} B"
    return f"{value:.3f} {units[unit_idx]}"


def human_seconds(seconds: float) -> str:
    minute = 60.0
    hour = 60.0 * minute
    day = 24.0 * hour
    year = 365.25 * day
    if seconds < minute:
        return f"{seconds:.3f} s"
    if seconds < hour:
        return f"{seconds / minute:.3f} min"
    if seconds < day:
        return f"{seconds / hour:.3f} h"
    if seconds < year:
        return f"{seconds / day:.3f} d"
    if seconds / year > 1e9:
        return f"{seconds / year:.3e} y"
    return f"{seconds / year:.3f} y"


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_task_specs(network: dict[str, object], replicate_idx: int) -> list[dict[str, object]]:
    n = network["n"]
    witness_rng = random.Random(10_000 + n * 97 + replicate_idx)
    witness_state = [witness_rng.randint(0, 1) for _ in range(n)]
    outputs = network_update(witness_state, network)
    task_defs = [
        ("T1_single", 1, 3),
        ("T2_small", 4, 5),
        ("T3_medium", 8, 7),
    ]
    specs: list[dict[str, object]] = []
    for name, query_size, offset in task_defs:
        query_nodes = choose_query_nodes(n, query_size, replicate_idx + offset)
        target_bits = [outputs[node - 1] for node in query_nodes]
        specs.append(
            {
                "task": name,
                "query_nodes": query_nodes,
                "target_bits": target_bits,
                "witness_state_prefix": witness_state[: min(16, len(witness_state))],
            }
        )
    return specs


def aggregate_results(exact_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[int, str], list[dict[str, object]]] = {}
    for row in exact_rows:
        grouped.setdefault((row["n"], row["task"]), []).append(row)

    aggregated: list[dict[str, object]] = []
    for (n, task), rows in sorted(grouped.items()):
        aggregated.append(
            {
                "n": n,
                "task": task,
                "replicates": len(rows),
                "median_wall_time_seconds": statistics.median(row["wall_time_seconds"] for row in rows),
                "max_wall_time_seconds": max(row["wall_time_seconds"] for row in rows),
                "median_peak_memory_bytes": int(statistics.median(row["peak_memory_bytes"] for row in rows)),
                "median_support_size": statistics.median(row["support_size"] for row in rows),
                "median_free_coordinates": statistics.median(row["free_coordinates"] for row in rows),
                "median_overlap_multiplicity": statistics.median(row["overlap_multiplicity"] for row in rows),
                "median_support_assignments_count": statistics.median(row["support_assignments_count"] for row in rows),
            }
        )
    return aggregated


def write_tex_rows(
    exact_agg: list[dict[str, object]],
    naive_rows: list[dict[str, object]],
) -> None:
    exact_lines = []
    for row in exact_agg:
        exact_lines.append(
            f"{row['n']} & {row['task']} & {row['median_support_size']} & {row['median_free_coordinates']} & "
            f"{row['median_overlap_multiplicity']} & {row['median_support_assignments_count']} & "
            f"{row['median_wall_time_seconds']:.6f} & {human_bytes(row['median_peak_memory_bytes'])} \\\\"
        )
    (BASE_DIR / "exact_method_rows.tex").write_text("\n".join(exact_lines) + "\n", encoding="utf-8")

    naive_lines = []
    for row in naive_rows:
        seconds_1e9 = row["throughput_seconds"]["1000000000"]
        naive_lines.append(
            f"{row['n']} & ${sci(row['rows'])}$ & ${sci(row['full_output_bits'])}$ & "
            f"{human_bytes(row['full_output_bytes'])} & {human_seconds(seconds_1e9)} \\\\"
        )
    (BASE_DIR / "naive_envelope_rows.tex").write_text("\n".join(naive_lines) + "\n", encoding="utf-8")

    synth_lines = []
    t3_lookup = {(row["n"], row["task"]): row for row in exact_agg}
    for row in naive_rows:
        t3 = t3_lookup[(row["n"], "T3_medium")]
        synth_lines.append(
            f"{row['n']} & {t3['median_support_size']} & {t3['median_wall_time_seconds']:.6f} & "
            f"{human_bytes(t3['median_peak_memory_bytes'])} & {human_bytes(row['full_output_bytes'])} & "
            f"{human_seconds(row['throughput_seconds']['1000000000'])} \\\\"
        )
    (BASE_DIR / "synthesis_rows.tex").write_text("\n".join(synth_lines) + "\n", encoding="utf-8")


def main() -> None:
    exact_rows: list[dict[str, object]] = []
    naive_rows: list[dict[str, object]] = []
    network_rows: list[dict[str, object]] = []
    session_lines = []

    for n in SIZES:
        naive = naive_resource_envelope(n)
        naive_rows.append(
            {
                "n": n,
                **naive,
            }
        )
        session_lines.append(
            f"[naive] n={n} rows={sci(naive['rows'])} full_bytes={human_bytes(naive['full_output_bytes'])} "
            f"time@1e9rows/s={human_seconds(naive['throughput_seconds']['1000000000'])}"
        )

        for replicate_idx in range(REPLICATES):
            seed = n * 100 + replicate_idx
            network = make_ring_local_network(n, seed)
            task_specs = build_task_specs(network, replicate_idx)
            network_rows.append(
                {
                    "n": n,
                    "replicate": replicate_idx,
                    "seed": seed,
                    "local_window": LOCAL_WINDOW,
                    "max_indegree": MAX_INDEGREE,
                }
            )

            for spec in task_specs:
                measured = measure_exact_method(network, spec["query_nodes"], spec["target_bits"])
                row = {
                    "n": n,
                    "replicate": replicate_idx,
                    "seed": seed,
                    "task": spec["task"],
                    "query_nodes": spec["query_nodes"],
                    "target_bits": spec["target_bits"],
                    "wall_time_seconds": measured["wall_time_seconds"],
                    "peak_memory_bytes": measured["peak_memory_bytes"],
                    "support_size": measured["support_size"],
                    "free_coordinates": measured["free_coordinates"],
                    "overlap_multiplicity": measured["overlap_multiplicity"],
                    "support_assignments_count": measured["support_assignments_count"],
                    "reduction_factor": measured["reduction_factor"],
                    "total_global_states": str(measured["total_global_states"]),
                    "support_union": measured["support_union"],
                    "support_assignments_sample": measured["support_assignments_sample"],
                }
                exact_rows.append(row)
                session_lines.append(
                    f"[exact] n={n} rep={replicate_idx} task={spec['task']} support={row['support_size']} "
                    f"free={row['free_coordinates']} overlap={row['overlap_multiplicity']} "
                    f"support_assignments={row['support_assignments_count']} time={row['wall_time_seconds']:.6f}s "
                    f"peak={human_bytes(row['peak_memory_bytes'])}"
                )

    exact_agg = aggregate_results(exact_rows)
    write_json(BASE_DIR / "exact_runs.json", exact_rows)
    write_json(BASE_DIR / "naive_envelope.json", naive_rows)
    write_json(BASE_DIR / "network_ensemble.json", network_rows)
    write_json(BASE_DIR / "scalability_summary.json", {"exact_aggregated": exact_agg, "naive": naive_rows})
    (BASE_DIR / "session_excerpt.txt").write_text("\n".join(session_lines) + "\n", encoding="utf-8")

    write_csv(
        BASE_DIR / "exact_runs.csv",
        exact_rows,
        [
            "n",
            "replicate",
            "seed",
            "task",
            "query_nodes",
            "target_bits",
            "wall_time_seconds",
            "peak_memory_bytes",
            "support_size",
            "free_coordinates",
            "overlap_multiplicity",
            "support_assignments_count",
            "reduction_factor",
            "total_global_states",
            "support_union",
            "support_assignments_sample",
        ],
    )
    write_csv(
        BASE_DIR / "exact_aggregated.csv",
        exact_agg,
        [
            "n",
            "task",
            "replicates",
            "median_wall_time_seconds",
            "max_wall_time_seconds",
            "median_peak_memory_bytes",
            "median_support_size",
            "median_free_coordinates",
            "median_overlap_multiplicity",
            "median_support_assignments_count",
        ],
    )
    write_csv(
        BASE_DIR / "naive_envelope.csv",
        [
            {
                "n": row["n"],
                "rows": str(row["rows"]),
                "full_output_bits": str(row["full_output_bits"]),
                "full_output_bytes": str(row["full_output_bytes"]),
                "time_seconds_1e6": row["throughput_seconds"]["1000000"],
                "time_seconds_1e8": row["throughput_seconds"]["100000000"],
                "time_seconds_1e9": row["throughput_seconds"]["1000000000"],
            }
            for row in naive_rows
        ],
        [
            "n",
            "rows",
            "full_output_bits",
            "full_output_bytes",
            "time_seconds_1e6",
            "time_seconds_1e8",
            "time_seconds_1e9",
        ],
    )
    write_tex_rows(exact_agg, naive_rows)


if __name__ == "__main__":
    main()
