"""Run every compared method on one public program and record what it did.

Owned by ``generate_figures.py``; it is the only place the paper executes a
compiler. Nothing is re-implemented: the serial and starter compilers come from
``.reference``, the classical compiler from ``common.py``, the Phase 1 direct
compiler from ``direct_compiler.py``, and R0, the shared branch state and C1
from ``research/``. The search runs on a logical clock with a fixed node limit
(the fixed-work mode of the confirmation), so every recorded count is
deterministic. No compile time is measured here; timing numbers in the paper
come only from frozen evidence rows.

Every numerical statement that a figure makes is asserted here before the data
are returned, and the notebook-04 outputs for the same computations are parsed
and compared, so the paper and the notebook cannot silently disagree.
"""
from __future__ import annotations

import collections
import contextlib
import hashlib
import importlib.util
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for entry in (str(ROOT / '.reference'), str(ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import machine  # noqa: E402
import common  # noqa: E402
import direct_contract as dc  # noqa: E402
import direct_compiler as dcomp  # noqa: E402
import schema_index as si  # noqa: E402
from research import structural_encoding as se  # noqa: E402
from research import efficiency_search as r0  # noqa: E402
from research import third_round_kernel as bs1  # noqa: E402
from research import third_round_candidate as c1  # noqa: E402
from research.optimization_common import object_sha256  # noqa: E402

PROGRAM = '05_mixed_broadcast'
SCALE_PROGRAM = '08_vector_reduction'
NODES = 10_000          # the confirmation's fixed-work node limit
C1_SHA = 'b9697640e202c7cf2563ef3f11423f6cbd52403f91c897b62a6ab1b044672cfa'
R0_SHA_PREFIX = 'd0fcd441'
RUN = ROOT / 'results/phase2_structural_encoding/third_round_20260925_resume'
NOTEBOOK = ROOT / 'notebooks/04-final-approach.ipynb'


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _starter():
    spec = importlib.util.spec_from_file_location('luminal_starter', ROOT / '.reference/compiler.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LogicalClock:
    """A clock that never advances: slices end by node count only."""

    def __call__(self):
        return 0.0


def fixed_work(module, program, facts, times, addresses, trace=None):
    stats = module.PropagationStats()
    return module.multiscale_optimise(
        program, facts, times, addresses, budget_seconds=0.1, node_ceiling=NODES,
        validation_ceiling=100_000, slice_nodes=2048, clock=LogicalClock(), stats=stats,
        trace=trace, catalog='a4', traversal='dfs')


def first_answer(program):
    facts = dc.derive(program)
    compiled, report = dcomp.compile_with_report(program, dcomp.DEFAULT_LIMITS, optimise=False)
    return facts, compiled, report, se.issue_cycles_of(program, compiled['bundles']), dict(compiled['scratch'])


@contextlib.contextmanager
def recorded_queries(log):
    """Record every cover the real bootstrap asks ``min_member`` about.

    Instrumentation only: it forwards to the owner and stores its argument and
    answer. The caller asserts that the instrumented compilation is identical to
    an uninstrumented one.
    """
    original, original_interval = si.min_member, si.interval
    pending = []

    def spy(cover):
        answer = original(cover)
        log.append(([(c.n, c.anchor, c.free_mask) for c in cover], answer, list(pending)))
        pending.clear()
        return answer

    def spy_interval(field, lo, hi, n):
        cubes = original_interval(field, lo, hi, n)
        pending.append({'field': field.name, 'lo': lo, 'hi': hi,
                        'cubes': [(c.n, c.anchor, c.free_mask) for c in cubes]})
        return cubes

    original_lowest = dcomp._lowest_address

    def spy_lowest(facts, name, *args, **kwargs):
        pending.append({'value': name})
        return original_lowest(facts, name, *args, **kwargs)

    si.min_member, si.interval, dcomp._lowest_address = spy, spy_interval, spy_lowest
    try:
        yield
    finally:
        si.min_member, si.interval, dcomp._lowest_address = original, original_interval, original_lowest


class CountingEdges(tuple):
    """The propagator's edge list, counting every look (as in notebook 04 section 10.3)."""

    looks = 0
    seen = []

    def __iter__(self):
        for edge in tuple.__iter__(self):
            CountingEdges.looks += 1
            CountingEdges.seen.append(edge)
            yield edge

    def __getitem__(self, index):
        CountingEdges.looks += 1
        edge = tuple.__getitem__(self, index)
        CountingEdges.seen.append(edge)
        return edge


def _notebook_outputs():
    cells = json.loads(NOTEBOOK.read_text())['cells']
    text = []
    for cell in cells:
        for out in cell.get('outputs', []):
            chunk = out.get('text') or out.get('data', {}).get('text/plain') or ''
            text.append(''.join(chunk))
    return '\n'.join(text)


def _layout(program, facts, compilation):
    times = se.issue_cycles_of(program, compilation['bundles'])
    addresses = dict(compilation['scratch'])
    C = machine.check_compilation(program, compilation)
    for case in program['cases']:
        machine.check_case(program, compilation, case)
    S = machine.scratch_footprint(program, compilation)
    assert se.objective(facts, times, addresses) == (C, S, C * S)
    life = dc.lifetimes(facts, times)
    return {'C': C, 'S': S, 'J': C * S, 'times': {str(k): v for k, v in times.items()},
            'addresses': addresses, 'lifetimes': {k: list(v) for k, v in life.items()}}


def compute():
    assert _sha(ROOT / 'research/third_round_candidate.py') == C1_SHA
    assert _sha(ROOT / 'research/efficiency_search.py').startswith(R0_SHA_PREFIX)
    program = machine.load_program(ROOT / f'.reference/programs/{PROGRAM}.json')
    facts = dc.derive(program)
    out = {'program': PROGRAM, 'program_object_sha256': object_sha256(program),
           'engine_limits': dict(machine.ENGINE_LIMITS)}
    out['operations'] = [
        {'id': op['id'], 'op': op['op'], 'engine': facts.engine[op['id']],
         'latency': facts.latency[op['id']], 'reads': list(op.get('args') or []),
         'writes': op.get('dest') or op.get('buffer')} for op in program['operations']]
    out['edges'] = [[u, v, lag] for v, preds in enumerate(facts.predecessors) for u, lag in preds.items()]
    out['widths'] = dict(facts.width)
    out['producers'] = dict(facts.producers)

    # The five compared methods on the same program.
    methods = {}
    methods['serial'] = _layout(program, facts, machine.serial_compile(program))
    methods['starter'] = _layout(program, facts, _starter().compile_program(program))
    methods['classical'] = _layout(program, facts, common.classical_compile(program))
    phase1, phase1_report = dcomp.compile_with_report(program, dcomp.DEFAULT_LIMITS, optimise=True)
    methods['direct_phase1'] = _layout(program, facts, phase1)

    log = []
    with recorded_queries(log):
        _, first, report, times0, addresses0 = first_answer(program)
    plain = dcomp.compile_with_report(program, dcomp.DEFAULT_LIMITS, optimise=False)[0]
    assert first == plain, 'instrumentation changed the bootstrap'
    first_layout = _layout(program, facts, first)
    assert (methods['direct_phase1']['C'], methods['direct_phase1']['S']) == (first_layout['C'], first_layout['S'])

    trace_r0, trace_c1 = [], []
    t_r0, a_r0, rec_r0 = fixed_work(r0, program, facts, times0, addresses0, trace_r0)
    t_c1, a_c1, rec_c1 = fixed_work(c1, program, facts, times0, addresses0, trace_c1)
    digest = lambda obj: hashlib.sha256(repr(obj).encode()).hexdigest()
    assert (t_r0, a_r0) == (t_c1, a_c1)
    assert digest(trace_r0) == digest(trace_c1)
    assert rec_r0['propagation']['certificate_stream_sha256'] == rec_c1['propagation']['certificate_stream_sha256']
    methods['C1'] = _layout(program, facts, dc.compilation(facts, t_c1, a_c1))
    out['methods'] = methods
    out['first_answer'] = first_layout
    out['first_answer_queries'] = report['bootstrap']['queries']

    # The frozen measured outputs must equal the live ones.
    frozen = [json.loads(line) for line in (RUN / 'stages/C_public/rows.jsonl').read_text().splitlines()]
    mine = {(r['arm_id'], r['cycles'], r['scratch']) for r in frozen
            if r['program_sha256'] == out['program_object_sha256'] and r['mode_key'] == 'wall:0.1'}
    assert mine == {('R0', methods['C1']['C'], methods['C1']['S']), ('C1', methods['C1']['C'], methods['C1']['S'])}, mine

    # Index queries of the first answer: one per operation, then one or more per value.
    queries = []
    for cover, answer, intervals in log:
        queries.append({'cubes': cover, 'chosen_index': answer, 'intervals': intervals})
    assert len(queries) >= facts.count
    schedule_queries = queries[:facts.count]
    width = dc.time_width(facts.horizon)
    field_t = si.Field('t', 0, width)
    for op_id, q in enumerate(schedule_queries):
        assert field_t.decode(q['chosen_index']) == times0[op_id]
        members = sorted({m for n, a, f in q['cubes'] for m in si.Cube(n, a, f).members()})
        assert min(members) == q['chosen_index']
        q['members'] = members
        q['labels'] = [si.Cube(n, a, f).label() for n, a, f in q['cubes']]
    out['time_width'] = width
    out['schedule_queries'] = schedule_queries
    field_a = si.Field('a', 0, dc.ADDRESS_WIDTH)
    address_queries = queries[facts.count:]
    order_seen = []
    for q in address_queries:
        names = [e['value'] for e in q['intervals'] if 'value' in e]
        q['intervals'] = [e for e in q['intervals'] if 'value' not in e]
        if names:
            q['value'] = names[0]
        q['decoded'] = field_a.decode(q['chosen_index']) if q['chosen_index'] is not None else None
        q['labels'] = [si.Cube(n, a, f).label() for n, a, f in q['cubes']]
        order_seen.append(q['decoded'])
    current = None
    for q in address_queries:
        current = q.get('value', current)
        q['value'] = current
        assert q['decoded'] == addresses0[current], (current, q['decoded'])
    assert [q['value'] for q in address_queries] and set(q['value'] for q in address_queries) == set(addresses0)
    out['address_queries'] = address_queries
    out['address_width'] = dc.ADDRESS_WIDTH

    # The anatomy of one question: k8_latest at the first answer.
    catalogue = r0.build_catalog(facts, times0, addresses0)
    out['catalogue'] = [{'policy': e['policy'], 'radius': e['radius'], 'window': list(e['window'])}
                        for e in catalogue]
    entry = next(e for e in catalogue if e['policy'] == 'k8_latest')
    caps = r0.product_caps(facts, times0, addresses0, entry['window'])
    assert caps['status'] == 'OK'
    assert caps['Scap'] == (caps['J0'] - 1) // caps['LC']
    assert caps['Ccap'] == min((caps['J0'] - 1) // caps['LS'], facts.horizon)
    out['caps'] = {k: caps[k] for k in ('J0', 'LC', 'LS', 'Ccap', 'Scap')}
    out['horizon'] = facts.horizon
    record = r0.product_record('k8_latest', program, facts, times0, addresses0,
                               entry['window'], entry['radius'], caps)
    question = se.Domain.from_record(record)
    declared = {op: tuple(question.time_domains[op]) for op in question.selected_operations}
    stats = r0.PropagationStats(keep=True)
    root = r0.Propagation(question, stats).times_fixpoint(declared)
    out['declared_domains'] = {str(k): list(v) for k, v in declared.items()}
    out['root_domains'] = {str(k): list(v) for k, v in root.items()}
    out['root_certificates'] = [list(c) for c in stats.certificates]
    out['combinations_declared'] = math.prod(len(v) for v in declared.values())
    out['combinations_root'] = math.prod(len(v) for v in root.values())
    for rule, u, v, lag, bound, removed in stats.certificates:
        assert rule in ('PL', 'PU')
        target = v if rule == 'PL' else u
        assert set(removed) <= set(declared[target]) and not set(removed) & set(root[target])
        if rule == 'PL':
            assert all(x < bound + lag for x in removed)

    # One decision and its consequences; then the same child built both ways.
    op, value = 0, 2
    child_stats = r0.PropagationStats(keep=True)
    fixed = dict(root)
    fixed[op] = (value,)
    child = r0.Propagation(question, child_stats).times_fixpoint(fixed)
    out['child_decision'] = [op, value]
    out['child_domains'] = {str(k): list(v) for k, v in child.items()}
    out['child_certificates'] = [list(c) for c in child_stats.certificates]

    stats_r0, stats_c1 = r0.PropagationStats(keep=True), r0.PropagationStats(keep=True)
    P_r0 = r0.Propagation(question, stats_r0)
    P_c1 = bs1.SharedPropagation(question, stats_c1)
    P_r0.edges = CountingEdges(P_r0.edges)
    P_c1.edges = CountingEdges(P_c1.edges)
    root_r0 = P_r0.times_fixpoint(declared)
    root_c1 = P_c1.time_root(declared)
    assert root_r0 == root_c1.D == root
    CountingEdges.looks = 0
    child_r0 = P_r0.times_fixpoint(fixed)
    looks_r0 = CountingEdges.looks
    CountingEdges.looks = 0
    CountingEdges.seen = []
    child_c1 = P_c1.time_child(root_c1, op, value)
    looks_c1 = CountingEdges.looks
    out['child_edges_looked_C1'] = [list(e) if isinstance(e, (tuple, list)) else e for e in CountingEdges.seen]
    out['propagator_edges'] = [list(e) if isinstance(e, (tuple, list)) else e for e in P_r0.edges]
    assert child_r0 == child_c1.D == child
    out['edges_total'] = len(P_r0.edges)
    out['child_edge_looks'] = {'R0': looks_r0, 'C1': looks_c1}
    out['change_record'] = sorted(child_c1.changed)
    changed_from_parent = sorted(o for o in root if tuple(child[o]) != tuple(root[o]))
    assert set(changed_from_parent) <= set(out['change_record'])

    def walk(limit):
        looks = [0, 0]
        nodes = 0
        stack = [(root_r0, root_c1)]
        while stack and nodes < limit:
            parent_r0, parent_c1 = stack.pop()
            free = [o for o in question.selected_operations if len(parent_r0[o]) > 1]
            if not free:
                continue
            o = free[0]
            for v in parent_r0[o]:
                CountingEdges.looks = 0
                trial = dict(parent_r0)
                trial[o] = (v,)
                a = P_r0.times_fixpoint(trial)
                looks[0] += CountingEdges.looks
                CountingEdges.looks = 0
                b = P_c1.time_child(parent_c1, o, v)
                looks[1] += CountingEdges.looks
                assert (a is None) == (b is None) and (a is None or a == b.D)
                nodes += 1
                if a is not None:
                    stack.append((a, b))
        return nodes, looks

    subtree = []
    for limit in (10, 100, 1000, 3000):
        stats_r0.certificates.clear()
        stats_c1.certificates.clear()
        nodes, (l0, l1) = walk(limit)
        assert stats_r0.certificates == stats_c1.certificates
        subtree.append({'limit': limit, 'children': nodes, 'looks_R0': l0, 'looks_C1': l1,
                        'certificates': len(stats_r0.certificates)})
    out['subtree'] = subtree

    # The epoch path of the whole search (identical for R0 and C1 at equal work).
    path = [[first_layout['C'], first_layout['S']]]
    steps = []
    for step in rec_r0['improvements']:
        steps.append({'epoch': step['epoch'], 'from': list(step['from_CS']), 'to': list(step['to_CS']),
                      'policy': step['policy'], 'radius': step['radius'], 'window': list(step['window'])})
        path.append(list(step['to_CS']))
    assert path[-1] == [methods['C1']['C'], methods['C1']['S']]
    out['epochs'] = {'count': rec_r0['epochs'], 'nodes': rec_r0['aggregate']['nodes'],
                     'stopped_because': rec_r0['stopped_because'], 'steps': steps, 'path': path,
                     'trace_sha256_R0': digest(trace_r0), 'trace_sha256_C1': digest(trace_c1),
                     'certificate_stream_sha256': rec_r0['propagation']['certificate_stream_sha256']}

    # Scale: the same comparison on a larger public program (counts only).
    big = machine.load_program(ROOT / f'.reference/programs/{SCALE_PROGRAM}.json')
    bfacts, bfirst, _, bt, ba = first_answer(big)
    bt0, ba0, brec0 = fixed_work(r0, big, bfacts, bt, ba)
    bt1, ba1, brec1 = fixed_work(c1, big, bfacts, bt, ba)
    assert (bt0, ba0) == (bt1, ba1)
    assert brec0['propagation']['certificate_stream_sha256'] == brec1['propagation']['certificate_stream_sha256']
    out['scale'] = {'program': SCALE_PROGRAM, 'operations': bfacts.count,
                    'first_CSJ': list(se.objective(bfacts, bt, ba)),
                    'final_CSJ': list(se.objective(bfacts, bt0, ba0)),
                    'nodes': brec0['aggregate']['nodes'], 'epochs': brec0['epochs']}

    # The two fresh programs of the Q1 finding: their first answers, and the
    # identity of the generated program with the one the frozen rows measured.
    from tests_direct import generate_programs as gp
    frozen_wall = [json.loads(line) for line in (RUN / 'stages/C_wall/rows.jsonl').read_text().splitlines()]
    out['q1'] = {}
    for seed in (980183, 980026):
        prog = gp.additional_program(seed)
        pf, _, _, pt, pa = first_answer(prog)
        hashes = {r['program_sha256'] for r in frozen_wall if r['seed'] == seed}
        assert hashes == {object_sha256(prog)}, seed
        out['q1'][str(seed)] = {'first_CSJ': list(se.objective(pf, pt, pa)), 'operations': pf.count}

    # The starter compiler on all eight public programs: equal to serial in C and S.
    starter = _starter()
    public = {}
    for path in sorted((ROOT / '.reference/programs').glob('*.json')):
        prog = machine.load_program(path)
        s_c = machine.serial_compile(prog)
        t_c = starter.compile_program(prog)
        pair = []
        for comp in (s_c, t_c):
            pair.append((machine.check_compilation(prog, comp), machine.scratch_footprint(prog, comp)))
            for case in prog['cases']:
                machine.check_case(prog, comp, case)
        assert pair[0] == pair[1], path.name
        public[path.stem] = {'serial': list(pair[0]), 'starter': list(pair[1]),
                             'object_sha256': object_sha256(prog)}
    ratio = math.prod(ser[0] * ser[1] / (st[0] * st[1]) for ser, st in
                      ((v['serial'], v['starter']) for v in public.values())) ** (1 / (2 * len(public)))
    out['starter_public'] = {'programs': public, 'score': ratio}

    # Cross-check against the recorded notebook-04 outputs for the same calls.
    text = _notebook_outputs()
    match = re.search(r'R0 looked at (\d+) edges, C1 looked at (\d+)', text)
    assert match and (int(match[1]), int(match[2])) == (looks_r0, looks_c1)
    last = re.findall(r'(\d+) children: edge looks R0\s+(\d+), C1\s+(\d+)', text)[-1]
    assert (int(last[0]), int(last[1]), int(last[2])) == (subtree[-1]['children'], subtree[-1]['looks_R0'], subtree[-1]['looks_C1'])
    assert f"combinations: {out['combinations_declared']:,} -> {out['combinations_root']:,}" in text
    assert f"{rec_r0['epochs']} epochs, {rec_r0['aggregate']['nodes']:,} nodes" in text
    out['notebook_cross_check'] = 'PASS: edge looks, subtree counts, combination counts and epoch/node counts equal notebook 04 outputs'
    return out


if __name__ == '__main__':
    data = compute()
    print(json.dumps({k: data[k] for k in ('child_edge_looks', 'subtree', 'epochs', 'scale', 'caps')}, indent=1))
