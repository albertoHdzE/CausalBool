"""Conventional and bounded index-query compilers; no public-case special cases."""
import argparse
import json
import sys
import time

from common import (allocate, bundles_for, classical_compile, dependencies, issue_times,
                    lifetimes, machine, objective, overlaps, widths)
from index_query import ConstraintQuery


def scheduling_query(program, compilation, selected, target):
    """Move a bounded operation set by at most two cycles; preserve allocation.

The query includes the target cycle bound, capacity, latency, memory ordering,
and all scratch lifetime conflicts, including consumers outside the window.
"""
    ops, times = program['operations'], issue_times(compilation)
    domains = {i: tuple(range(max(0, t-2), min(t+2, target-1)+1))
               if i in selected else (t,) for i, t in times.items()}
    if any(not d for d in domains.values()):
        return None
    query = ConstraintQuery(dict(sorted(domains.items())))
    for i in times:
        query.add((i,), lambda t, target=target: t < target, 'cycle target')
    for i, predecessors in enumerate(dependencies(program)):
        for p, lag in predecessors.items():
            query.add((p, i), lambda a, b, lag=lag: a + lag <= b, 'precedence')
    for engine, limit in machine.ENGINE_LIMITS.items():
        ids = tuple(op['id'] for op in ops if machine.OP_SPECS[op['op']]['engine'] == engine)
        for cycle in range(max(times.values()) + 3):
            relevant = tuple(i for i in ids if cycle in domains[i])
            if len(relevant) > limit:
                query.add(relevant, lambda *ts, c=cycle, k=limit: sum(t == c for t in ts) <= k,
                          'engine capacity')
    size = widths(program)
    producers = machine.producer_map(program)
    consumers = {name: [] for name in producers}
    for op in ops:
        for name in set(op.get('args', [])):
            consumers[name].append(op['id'])
    names = list(producers)
    for j, a in enumerate(names):
        for b in names[j+1:]:
            aa, bb = compilation['scratch'][a], compilation['scratch'][b]
            if not (aa < bb + size[b] and bb < aa + size[a]):
                continue
            pa, pb = producers[a], producers[b]
            la = machine.OP_SPECS[ops[pa]['op']]['latency']
            lb = machine.OP_SPECS[ops[pb]['op']]['latency']
            ca, cb = tuple(consumers[a]), tuple(consumers[b])
            scope = tuple(dict.fromkeys((pa, pb) + ca + cb))

            def safe(*ts, scope=scope, pa=pa, pb=pb, la=la, lb=lb, ca=ca, cb=cb):
                t = dict(zip(scope, ts))
                sa, sb = t[pa]+la, t[pb]+lb
                ea = max([sa] + [t[i] for i in ca])
                eb = max([sb] + [t[i] for i in cb])
                return ea < sb or eb < sa

            query.add(scope, safe, 'scratch lifetime')
    return query


def allocation_query(program, compilation, selected, target):
    """Find aligned addresses within a footprint bound, holding schedule fixed."""
    size = widths(program)
    live = lifetimes(program, issue_times(compilation))
    domains = {name: tuple(range(0, target-size[name]+1, size[name]))
               if name in selected else (base,) for name, base in compilation['scratch'].items()}
    if any(not d for d in domains.values()):
        return None
    query = ConstraintQuery(domains)
    for name in domains:
        query.add((name,), lambda a, w=size[name], m=target: a + w <= m, 'scratch target')
    names = list(domains)
    for i, a in enumerate(names):
        for b in names[i+1:]:
            if overlaps(live[a], live[b]):
                query.add((a, b), lambda aa, bb, wa=size[a], wb=size[b]:
                          aa + wa <= bb or bb + wb <= aa, 'live address conflict')
    return query


def optimize(program, method='index', query_seconds=0.12, total_seconds=2.0):
    start = time.perf_counter()
    compilation = classical_compile(program)
    reports = []
    for _ in range(2):
        times = issue_times(compilation)
        # Two overlapping suffix windows. External operations remain in every query.
        ordered = sorted(times, key=lambda i: (-times[i], i))
        groups = [ordered[:6], ordered[:3] + ordered[6:9]]
        for group in groups:
            if time.perf_counter()-start >= total_seconds:
                return compilation, reports
            target = len(compilation['bundles'])-1
            query = scheduling_query(program, compilation, set(group), target)
            if query is None:
                continue
            answer, report = getattr(query, 'solve_' + method)(seconds=query_seconds)
            report.update(kind='schedule', target=target, accepted=False)
            reports.append(report)
            if answer is not None:
                candidate = {'scratch': dict(compilation['scratch']),
                             'bundles': bundles_for(program, answer)}
                machine.check_compilation(program, candidate)
                packed = allocate(program, answer)
                if max((packed[n]+widths(program)[n] for n in packed), default=0) < machine.scratch_footprint(program, candidate):
                    candidate['scratch'] = packed
                if objective(program, candidate) < objective(program, compilation):
                    compilation = candidate
                    report['accepted'] = True
        size = widths(program)
        names = sorted(size, key=lambda n: (-compilation['scratch'][n]-size[n], n))
        for group in (names[:4], names[:2]+names[4:6]):
            if time.perf_counter()-start >= total_seconds:
                return compilation, reports
            target = machine.scratch_footprint(program, compilation)-1
            query = allocation_query(program, compilation, set(group), target)
            if query is None:
                continue
            answer, report = getattr(query, 'solve_' + method)(seconds=query_seconds)
            report.update(kind='allocation', target=target, accepted=False)
            reports.append(report)
            if answer is not None:
                candidate = {'scratch': answer, 'bundles': compilation['bundles']}
                machine.check_compilation(program, candidate)
                if objective(program, candidate) < objective(program, compilation):
                    compilation = candidate
                    report['accepted'] = True
    return compilation, reports


def compile_program(program):
    return optimize(program)[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('program')
    parser.add_argument('--method', choices=('serial', 'classical', 'index', 'exhaustive'), default='index')
    args = parser.parse_args()
    program = machine.load_program(args.program)
    if args.method == 'serial':
        result = machine.serial_compile(program)
    elif args.method == 'classical':
        result = classical_compile(program)
    else:
        result, _ = optimize(program, args.method)
    machine.check_compilation(program, result)
    json.dump(result, sys.stdout, sort_keys=True)
    print()


if __name__ == '__main__':
    main()
