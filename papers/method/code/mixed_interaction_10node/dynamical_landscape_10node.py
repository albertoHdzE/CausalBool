from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

CM10 = [
    [0, 1, 1, 0, 0, 0, 0, 0, 0, 0],
    [1, 0, 1, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 0, 0, 0],
    [0, 1, 1, 0, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
    [0, 0, 0, 0, 1, 0, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
    [1, 0, 0, 0, 0, 0, 0, 0, 1, 0],
    [0, 1, 0, 0, 0, 0, 0, 0, 0, 1],
    [0, 0, 1, 1, 0, 0, 1, 1, 0, 0],
]

DYN10 = ["AND", "OR", "XOR", "KOFN", "NOR", "XNOR", "NOT", "IMPLIES", "NIMPLIES", "MAJORITY"]
PARAMS10 = {4: {"k": 2}, 8: {"pair": (1, 9)}, 9: {"pair": (2, 10)}}


def bits_to_str(bits: tuple[int, ...] | list[int]) -> str:
    return "".join(str(x) for x in bits)


def gate(name: str, inputs: list[int], params: dict | None = None) -> int:
    params = params or {}
    if name == "AND":
        return int(all(inputs))
    if name == "OR":
        return int(any(inputs))
    if name == "XOR":
        return sum(inputs) % 2
    if name == "NOR":
        return int(not any(inputs))
    if name == "XNOR":
        return 1 - (sum(inputs) % 2)
    if name == "NOT":
        return 1 - inputs[0]
    if name == "IMPLIES":
        return int((1 - inputs[0]) or inputs[1])
    if name == "NIMPLIES":
        return int(inputs[0] and (1 - inputs[1]))
    if name == "KOFN":
        return int(sum(inputs) >= params["k"])
    if name == "MAJORITY":
        return int(sum(inputs) > len(inputs) // 2)
    raise ValueError(name)


def next_state(state: tuple[int, ...]) -> tuple[int, ...]:
    out: list[int] = []
    for i, row in enumerate(CM10, start=1):
        coords = [j + 1 for j, val in enumerate(row) if val == 1]
        if DYN10[i - 1] in {"IMPLIES", "NIMPLIES"}:
            pair = PARAMS10[i]["pair"]
            inputs = [state[pair[0] - 1], state[pair[1] - 1]]
        elif DYN10[i - 1] == "NOT":
            inputs = [state[coords[0] - 1]]
        else:
            inputs = [state[j - 1] for j in coords]
        out.append(gate(DYN10[i - 1], inputs, PARAMS10.get(i)))
    return tuple(out)


def state_from_index(idx: int, n: int = 10) -> tuple[int, ...]:
    value = idx - 1
    return tuple((value >> i) & 1 for i in range(n))


def functional_cycles(next_indices: list[int]) -> list[list[int]]:
    n = len(next_indices)
    status = [0] * n
    cycles: list[list[int]] = []
    for start in range(n):
        if status[start]:
            continue
        path: list[int] = []
        pos: dict[int, int] = {}
        cur = start
        while not status[cur] and cur not in pos:
            pos[cur] = len(path)
            path.append(cur)
            cur = next_indices[cur]
        if cur in pos:
            cycles.append(path[pos[cur] :])
        for node in path:
            status[node] = 1
    return cycles


def write_text(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    states = [state_from_index(i) for i in range(1, 2**10 + 1)]
    state_to_index = {state: i for i, state in enumerate(states, start=1)}
    next_states = [next_state(state) for state in states]
    next_indices = [state_to_index[state] for state in next_states]
    image_states = sorted(set(next_states), key=lambda s: state_to_index[s])
    cycles_idx = functional_cycles([i - 1 for i in next_indices])
    cycles = [[states[j] for j in cyc] for cyc in cycles_idx]
    cycle_id_by_state = {state: k + 1 for k, cyc in enumerate(cycles) for state in cyc}

    def eventual_cycle_id(state: tuple[int, ...]) -> int:
        current = state
        while current not in cycle_id_by_state:
            current = next_state(current)
        return cycle_id_by_state[current]

    def transient_length(state: tuple[int, ...]) -> int:
        current = state
        steps = 0
        while current not in cycle_id_by_state:
            current = next_state(current)
            steps += 1
        return steps

    basin_sizes = Counter(eventual_cycle_id(state) for state in states)
    cycle_summary = [
        {
            "CycleID": k + 1,
            "Period": len(cyc),
            "States": [bits_to_str(s) for s in cyc],
            "BasinSize": basin_sizes[k + 1],
        }
        for k, cyc in enumerate(cycles)
    ]

    full_cases = {
        "F1": tuple(int(c) for c in "1111111111"),
        "F2": tuple(int(c) for c in "1111111110"),
        "F3": tuple(int(c) for c in "1111111101"),
        "F4": tuple(int(c) for c in "1111101111"),
    }

    full_status = []
    for name, pattern in full_cases.items():
        full_status.append(
            {
                "Name": name,
                "Pattern": bits_to_str(pattern),
                "StateIndex": state_to_index[pattern],
                "Reachable": pattern in image_states,
                "Recurrent": pattern in cycle_id_by_state,
                "CycleID": eventual_cycle_id(pattern),
                "TransientLength": transient_length(pattern),
                "NextState": bits_to_str(next_state(pattern)),
            }
        )

    subsystem_specs = {
        "S1": {"nodes": (4, 6, 7, 10), "projection": (0, 1, 1, 1)},
        "S2": {"nodes": (4, 6, 7, 8, 9, 10), "projection": (0, 1, 1, 1, 0, 1)},
    }

    subsystem_status = []
    for name, spec in subsystem_specs.items():
        rows = []
        outputs = []
        for idx, out in enumerate(next_states, start=1):
            proj = tuple(out[i - 1] for i in spec["nodes"])
            if proj == spec["projection"]:
                rows.append(idx)
                outputs.append(out)
        distinct_outputs = sorted(set(outputs), key=lambda s: state_to_index[s])
        recurrent_outputs = [out for out in distinct_outputs if out in cycle_id_by_state]
        subsystem_status.append(
            {
                "Name": name,
                "Projection": bits_to_str(spec["projection"]),
                "RowCount": len(rows),
                "DistinctOutputs": [bits_to_str(o) for o in distinct_outputs],
                "DistinctOutputCount": len(distinct_outputs),
                "RecurrentOutputs": [bits_to_str(o) for o in recurrent_outputs],
                "RecurrentCount": len(recurrent_outputs),
                "CycleIDs": sorted({eventual_cycle_id(o) for o in distinct_outputs}),
            }
        )

    sample_rows = []
    for row in full_status:
        sample_rows.append(row)
    for row in subsystem_status:
        for pattern in row["DistinctOutputs"]:
            state = tuple(int(c) for c in pattern)
            sample_rows.append(
                {
                    "Name": row["Name"],
                    "Pattern": pattern,
                    "StateIndex": state_to_index[state],
                    "Reachable": True,
                    "Recurrent": state in cycle_id_by_state,
                    "CycleID": eventual_cycle_id(state),
                    "TransientLength": transient_length(state),
                    "NextState": bits_to_str(next_state(state)),
                }
            )

    cycle_rows = [
        f"{row['CycleID']} & {row['Period']} & {row['BasinSize']} & \\(\\{{{', '.join(row['States'])}\\}}\\) \\\\"
        for row in cycle_summary
    ]
    case_rows = []
    for row in full_status:
        case_rows.append(
            f"{row['Name']} & full & \\texttt{{{row['Pattern']}}} & {row['StateIndex']} & "
            f"{'yes' if row['Reachable'] else 'no'} & {'yes' if row['Recurrent'] else 'no'} & "
            f"A_{row['CycleID']} & {row['TransientLength']} \\\\"
        )
    for row in subsystem_status:
        rec = f"{row['RecurrentCount']} outputs" if row["RecurrentCount"] else "no"
        cycles_tex = ", ".join(f"A_{cid}" for cid in row["CycleIDs"])
        case_rows.append(
            f"{row['Name']} & subsystem & \\texttt{{{row['Projection']}}} & "
            f"{row['RowCount']} rows / {row['DistinctOutputCount']} outputs & yes & {rec} & "
            f"\\(\\{{{cycles_tex}\\}}\\) & --- \\\\"
        )
    sample_tex_rows = [
        f"{row['Name']} & \\texttt{{{row['Pattern']}}} & {row['StateIndex']} & "
        f"\\texttt{{{row['NextState']}}} & {'yes' if row['Recurrent'] else 'no'} & "
        f"A_{row['CycleID']} & {row['TransientLength']} \\\\"
        for row in sample_rows
    ]

    session_lines = [
        f"In := imageSize10 = {len(image_states)}",
        f"In := cycleSummary10 = {json.dumps(cycle_summary)}",
        f"In := fullStatus10 = {json.dumps(full_status)}",
        f"In := subsystemStatus10 = {json.dumps(subsystem_status)}",
        "Out = True",
    ]

    summary = {
        "ImageSize": len(image_states),
        "ImageStates": [bits_to_str(s) for s in image_states],
        "CycleSummary": cycle_summary,
        "FullStatus": full_status,
        "SubsystemStatus": subsystem_status,
        "SampleRows": sample_rows,
    }

    write_text(BASE_DIR / "dynamical_cycle_rows.tex", cycle_rows)
    write_text(BASE_DIR / "dynamical_case_rows.tex", case_rows)
    write_text(BASE_DIR / "dynamical_sample_rows.tex", sample_tex_rows)
    write_text(BASE_DIR / "dynamical_session_excerpt.txt", session_lines)
    (BASE_DIR / "dynamical_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
