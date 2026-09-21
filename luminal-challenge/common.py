"""Shared, deterministic compiler machinery for the paired experiment."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.reference'))
import machine


def dependencies(program):
    ops = program['operations']
    producers = machine.producer_map(program)
    predecessors = [{} for _ in ops]
    for op in ops:
        incoming = predecessors[op['id']]
        for arg in op.get('args', []):
            p = producers[arg]
            incoming[p] = machine.OP_SPECS[ops[p]['op']]['latency']
        for p in machine.memory_predecessors(program, op['id']):
            incoming[p] = max(incoming.get(p, 0), 1)
    return predecessors


def issue_times(compilation):
    return {i: t for t, bundle in enumerate(compilation['bundles'])
            for ids in bundle.values() for i in ids}


def bundles_for(program, times):
    bundles = [{} for _ in range(max(times.values()) + 1)]
    for op in program['operations']:
        engine = machine.OP_SPECS[op['op']]['engine']
        bundles[times[op['id']]].setdefault(engine, []).append(op['id'])
    return bundles


def lifetimes(program, times):
    lives = {}
    for op in program['operations']:
        if 'dest' in op:
            ready = times[op['id']] + machine.OP_SPECS[op['op']]['latency']
            lives[op['dest']] = [ready, ready]
    for op in program['operations']:
        for arg in op.get('args', []):
            lives[arg][1] = max(lives[arg][1], times[op['id']])
    return lives


def widths(program):
    return {name: machine.VLEN if kind == 'vector' else 1
            for name, kind in machine.result_kinds(program).items()}


def overlaps(a, b):
    return a[0] <= b[1] and b[0] <= a[1]


def allocate(program, times):
    """Aligned first fit over inclusive live intervals, with three fixed orders."""
    live, size = lifetimes(program, times), widths(program)
    degree = {a: sum(overlaps(live[a], live[b]) for b in live if a != b) for a in live}
    orders = [sorted(live, key=lambda a: (-size[a], -degree[a], live[a][0], a)),
              sorted(live, key=lambda a: (live[a][0], -size[a], a)),
              sorted(live, key=lambda a: (-size[a], live[a][0], a))]
    candidates = []
    for order in orders:
        assigned = {}
        for a in order:
            for address in range(0, machine.SCRATCH_WORDS - size[a] + 1, size[a]):
                if all(not (overlaps(live[a], live[b]) and
                            address < base + size[b] and base < address + size[a])
                       for b, base in assigned.items()):
                    assigned[a] = address
                    break
            else:
                break
        if len(assigned) == len(live):
            candidates.append(assigned)
    if not candidates:
        raise machine.CompileError('first-fit allocation exhausted scratch')
    return min(candidates, key=lambda a: max((a[v] + size[v] for v in a), default=0))


def classical_compile(program):
    """Critical-path list scheduling plus live-interval scratch reuse."""
    ops = program['operations']
    preds = dependencies(program)
    successors = [[] for _ in ops]
    for i, ps in enumerate(preds):
        for p, lag in ps.items():
            successors[p].append((i, lag))
    heights = [0] * len(ops)
    for i in reversed(range(len(ops))):
        heights[i] = max((lag + heights[j] for j, lag in successors[i]), default=0)
    times, pending, cycle = {}, set(range(len(ops))), 0
    while pending:
        ready = [i for i in pending if all(p in times and times[p] + lag <= cycle
                                          for p, lag in preds[i].items())]
        used = dict.fromkeys(machine.ENGINE_LIMITS, 0)
        for i in sorted(ready, key=lambda i: (-heights[i], -len(successors[i]), i)):
            engine = machine.OP_SPECS[ops[i]['op']]['engine']
            if used[engine] < machine.ENGINE_LIMITS[engine]:
                times[i] = cycle
                pending.remove(i)
                used[engine] += 1
        cycle += 1
    try:
        candidate = {'scratch': allocate(program, times), 'bundles': bundles_for(program, times)}
        machine.check_compilation(program, candidate)
    except machine.CompileError:
        return machine.serial_compile(program)
    baseline = machine.serial_compile(program)
    return min((candidate, baseline), key=lambda c: objective(program, c))


def objective(program, compilation):
    return len(compilation['bundles']) * machine.scratch_footprint(program, compilation)
