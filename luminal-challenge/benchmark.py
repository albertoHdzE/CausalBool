"""Frozen public validation, fresh-process timing, and matched-query controls."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import sys
import time
import types
import unittest

from common import ROOT, classical_compile, issue_times, machine
from compilers import allocation_query, optimize, scheduling_query
from index_query import SOURCE


def verify_reference():
    manifest = json.loads((ROOT/'reference.json').read_text())
    for name, expected in manifest['sha256'].items():
        if hashlib.sha256((ROOT/'.reference'/name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('reference changed: ' + name)
    return manifest['commit']


def compile_method(program, method):
    if method == 'serial':
        return machine.serial_compile(program), []
    if method == 'classical':
        return classical_compile(program), []
    return optimize(program, method)


def worker(method, path):
    program = machine.load_program(path)
    start = time.perf_counter()
    compilation, queries = compile_method(program, method)
    elapsed = time.perf_counter()-start
    compile_peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform != 'darwin':
        compile_peak *= 1024
    cycles = machine.check_compilation(program, compilation)
    for case in program['cases']:
        machine.check_case(program, compilation, case)
    return dict(cycles=cycles, scratch=machine.scratch_footprint(program, compilation),
                compile_seconds=elapsed, process_peak_rss_bytes=compile_peak,
                correctness='PASS', queries=queries)


def frozen_tests(method):
    # Supply the compiler under test via the unchanged public test import contract.
    # unittest reuses imported test modules: preserve their module reference
    # while replacing the callable, so every arm actually runs its own compiler.
    compiler = sys.modules.get('compiler', types.ModuleType('compiler'))
    compiler.compile_program = lambda p: compile_method(p, method)[0]
    sys.modules['compiler'] = compiler
    suite = unittest.defaultTestLoader.discover(str(ROOT/'.reference/tests'),
                                               top_level_dir=str(ROOT/'.reference'))
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    if not result.wasSuccessful():
        raise RuntimeError('frozen public tests failed for ' + method)
    return result.testsRun


def matched_queries(program):
    baseline = classical_compile(program)
    ordered = sorted(issue_times(baseline), key=lambda i: (-issue_times(baseline)[i], i))
    names = sorted(baseline['scratch'], key=lambda n: (-baseline['scratch'][n], n))
    records = []
    for delta in (0, 1):
        for kind in ('schedule', 'allocation'):
            if kind == 'schedule':
                target = len(baseline['bundles'])-delta
                query = scheduling_query(program, baseline, set(ordered[:6]), target)
            else:
                target = machine.scratch_footprint(program, baseline)-delta
                query = allocation_query(program, baseline, set(names[:4]), target)
            if query is None:
                continue
            a, ia = query.solve_index(seconds=0.12)
            b, ib = query.solve_exhaustive(seconds=0.12)
            comparable = ia['status'] != 'UNKNOWN' and ib['status'] != 'UNKNOWN'
            if comparable and (ia['status'] != ib['status'] or a != b):
                raise AssertionError('matched query solvers disagree')
            records.append(dict(kind=kind, target=target, tightening=delta,
                                index=ia, exhaustive=ib, comparable=comparable,
                                exact_agreement=comparable and a == b))
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', choices=('serial', 'classical', 'index', 'exhaustive'))
    parser.add_argument('--program')
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args.worker, args.program)))
        return
    if args.repeats < 1:
        parser.error('--repeats must be positive')
    commit = verify_reference()
    methods = ('serial', 'classical', 'index', 'exhaustive')
    tests = {method: frozen_tests(method) for method in methods}
    records = []
    paths = sorted((ROOT/'.reference/programs').glob('*.json'))
    if len(paths) != 8:
        raise RuntimeError('expected exactly eight public programs')
    for path in paths:
        p = machine.load_program(path)
        runs = {method: [] for method in methods}
        # Rotate execution order to reduce a fixed method-order timing bias.
        for repeat in range(args.repeats):
            for method in methods[repeat % 4:] + methods[:repeat % 4]:
                result = subprocess.run([sys.executable, __file__, '--worker', method,
                                         '--program', str(path)], capture_output=True, text=True,
                                        check=True, timeout=20)
                runs[method].append(json.loads(result.stdout))
        records.append(dict(program=p['name'], runs=runs, matched_queries=matched_queries(p)))
        print(p['name'] + ': ' + ', '.join(f'{m}={runs[m][0]["cycles"]} cycles/{runs[m][0]["scratch"]} words'
                                         for m in methods), flush=True)
    summary = {}
    for method in methods:
        speedups, reductions = [], []
        for r in records:
            baseline = r['runs']['serial'][0]
            metrics = {(run['cycles'], run['scratch']) for run in r['runs'][method]}
            if len(metrics) != 1:
                raise RuntimeError('resource-limited scores varied between repeats; report runs explicitly')
            cycles, words = next(iter(metrics))
            speedups.append(baseline['cycles']/cycles)
            reductions.append(baseline['scratch']/words)
        speedup = math.exp(statistics.mean(map(math.log, speedups)))
        reduction = math.exp(statistics.mean(map(math.log, reductions)))
        summary[method] = dict(cycle_speedup_geomean=speedup, scratch_reduction_geomean=reduction,
                               combined_score=math.sqrt(speedup*reduction),
                               median_compile_seconds=statistics.median(run['compile_seconds']
                                   for r in records for run in r['runs'][method]),
                               max_process_peak_rss_bytes=max(run['process_peak_rss_bytes']
                                   for r in records for run in r['runs'][method]))
    sources = list(ROOT.glob('*.py')) + [SOURCE]
    report = dict(reference_commit=commit, python=sys.version, platform=platform.platform(),
                  repetitions=args.repeats, frozen_tests=tests, summary=summary, programs=records,
                  source_sha256={str(p.relative_to(ROOT.parent)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in sources},
                  limitations=['Public programs only; private grader unavailable.',
                               'Index/exhaustive arms share a classical starting compilation.',
                               'Exact queries cover bounded neighborhoods; UNSAT is local.',
                               'RSS includes interpreter/imports; compile timing excludes process startup.',
                               'Logical decision bits exclude variable-domain mapping, predicates and decoder.',
                               'No paper-level asymptotic or novelty claim follows from this pilot.'])
    (ROOT/'results').mkdir(exist_ok=True)
    (ROOT/'results/comparison.json').write_text(json.dumps(report, indent=2)+'\n')
    lines = ['# Public pilot comparison', '',
             '| Method | Cycle speedup | Scratch reduction | Combined score | Median compile ms |',
             '|---|---:|---:|---:|---:|']
    for method, row in summary.items():
        lines.append(f'| {method} | {row["cycle_speedup_geomean"]:.3f}x | '
                     f'{row["scratch_reduction_geomean"]:.3f}x | {row["combined_score"]:.3f}x | '
                     f'{1000*row["median_compile_seconds"]:.3f} |')
    query_rows = [q for r in records for q in r['matched_queries']]
    lines += ['', f'{len(query_rows)} identical-query controls; '
              f'{sum(q["comparable"] for q in query_rows)} completed in both solvers, '
              f'{sum(q["exact_agreement"] for q in query_rows)} agreed exactly.', '',
              'Status counts: ' + json.dumps({m: dict(Counter(q[m]['status'] for q in query_rows))
                                              for m in ('index', 'exhaustive')}) + '.', '',
              'Scores are relative to the frozen serial compiler. Index and exhaustive are bounded',
              'improvement passes over the same classical compiler. Equal scores do not establish',
              'global optimality. This pilot does not establish an index-method advantage over',
              'conventional compiler optimization.', '',
              'See comparison.json for all runs, source hashes, query timings, node allocations,',
              'witness anchors/free masks, process memory, and limitations.', '']
    (ROOT/'results/COMPARISON.md').write_text('\n'.join(lines))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
