"""Independent constraint/certificate checks and compiler regression tests."""
from itertools import product
from pathlib import Path
import random
import unittest

from common import ROOT, classical_compile, machine, objective
from compilers import allocation_query, optimize, scheduling_query
from index_query import ConstraintQuery


def generated_program(seed, count=25):
    rng = random.Random(seed)
    ops, available = [], {'scalar': [], 'vector': []}
    def emit(opcode):
        spec = machine.OP_SPECS[opcode]
        op = {'id': len(ops), 'op': opcode}
        if spec['args']:
            op['args'] = [rng.choice(available[k]) for k in spec['args']]
        if spec['result']:
            op['dest'] = 'v' + str(len(ops))
            available[spec['result']].append(op['dest'])
        if opcode == 'const':
            op['value'] = rng.randrange(-(1 << 32), 1 << 33)
        if opcode in machine.MEMORY_OPS:
            op['buffer'] = 'data'
            op['offset'] = rng.randrange(17-machine.memory_width(op))
        ops.append(op)
    emit('const')
    emit('vload')
    for _ in range(count-2):
        emit(rng.choice(tuple(machine.OP_SPECS)))
    emit('store')
    emit('vstore')
    p = {'name': 'generated_' + str(seed), 'buffers': {'data': 16}, 'operations': ops,
         'cases': [{'data': [rng.getrandbits(32) for _ in range(16)]} for _ in range(2)]}
    machine.validate_program(p)
    return p


class QueryTests(unittest.TestCase):
    def test_improved_schedule_is_returned_by_the_query(self):
        from common import bundles_for
        p = {'name': 'two_independent_constants', 'buffers': {'out': 2},
             'operations': [
                 {'id': 0, 'op': 'const', 'dest': 'a', 'value': 3},
                 {'id': 1, 'op': 'const', 'dest': 'b', 'value': 7},
                 {'id': 2, 'op': 'store', 'args': ['a'], 'buffer': 'out', 'offset': 0},
                 {'id': 3, 'op': 'store', 'args': ['b'], 'buffer': 'out', 'offset': 1}],
             'cases': [{'out': [0, 0]}]}
        serial = machine.serial_compile(p)
        q = scheduling_query(p, serial, set(range(4)), len(serial['bundles'])-1)
        answer, report = q.solve_index(seconds=1)
        self.assertEqual(report['status'], 'SAT')
        candidate = {'scratch': serial['scratch'], 'bundles': bundles_for(p, answer)}
        self.assertLess(len(candidate['bundles']), len(serial['bundles']))
        machine.check_case(p, candidate, p['cases'][0])

    def test_exact_symbolic_and_exhaustive_agreement(self):
        for seed in range(25):
            rng = random.Random(seed)
            q = ConstraintQuery({'a': range(3), 'b': range(4), 'c': range(2)})
            allowed = {(a, b) for a in range(3) for b in range(4) if rng.randrange(2)}
            q.add(('a', 'b'), lambda a, b, s=allowed: (a, b) in s, 'random relation')
            q.add(('b', 'c'), lambda b, c: b % 2 == c, 'parity')
            a, ra = q.solve_index(seconds=1)
            b, rb = q.solve_exhaustive(seconds=1)
            self.assertEqual(ra['status'], rb['status'])
            self.assertEqual(a, b)
            if a is not None:
                # Every filling of the returned sumandos must satisfy every rule.
                free = [i for i in range(q.n) if ra['free_mask'] >> i & 1]
                for bits in product((0, 1), repeat=len(free)):
                    row = ra['decimal_anchor'] + sum(v << i for v, i in zip(bits, free))
                    self.assertTrue(q.accepts(q.decode(row)))

    def test_unsat_and_resource_limit_are_distinct(self):
        q = ConstraintQuery({'a': (0, 1)})
        q.add(('a',), lambda a: a == 0, 'zero')
        q.add(('a',), lambda a: a == 1, 'one')
        self.assertEqual(q.solve_index()[1]['status'], 'UNSAT')
        self.assertEqual(q.solve_index(max_nodes=0)[1]['status'], 'UNKNOWN')

    def test_allocation_query_matches_machine_for_every_candidate(self):
        p = generated_program(42, count=8)
        c = classical_compile(p)
        names = list(c['scratch'])[:2]
        q = allocation_query(p, c, set(names), machine.scratch_footprint(p, c))
        for values in product(*q.domains.values()):
            assignment = dict(zip(q.domains, values))
            candidate = {'scratch': assignment, 'bundles': c['bundles']}
            try:
                machine.check_compilation(p, candidate)
                valid = True
            except machine.CompileError:
                valid = False
            self.assertEqual(valid, q.accepts(assignment))

    def test_schedule_query_matches_machine_for_every_candidate(self):
        from common import bundles_for
        for seed in range(6):
            p = generated_program(seed, count=8)
            c = classical_compile(p)
            q = scheduling_query(p, c, {0, 1, 2}, len(c['bundles']))
            for values in product(*q.domains.values()):
                assignment = dict(zip(q.domains, values))
                candidate = {'scratch': c['scratch'], 'bundles': bundles_for(p, assignment)}
                try:
                    machine.check_compilation(p, candidate)
                    valid = len(candidate['bundles']) <= len(c['bundles'])
                except machine.CompileError:
                    valid = False
                self.assertEqual(valid, q.accepts(assignment))


class CompilerTests(unittest.TestCase):
    def test_public_and_generated(self):
        programs = [machine.load_program(p) for p in sorted((ROOT/'.reference/programs').glob('*.json'))]
        self.assertEqual(len(programs), 8)
        programs += [generated_program(seed) for seed in range(30)]
        for p in programs:
            with self.subTest(program=p['name']):
                baseline = classical_compile(p)
                indexed, _ = optimize(p, query_seconds=0.025, total_seconds=0.3)
                self.assertLessEqual(objective(p, indexed), objective(p, baseline))
                for c in (baseline, indexed):
                    machine.check_compilation(p, c)
                    for case in p['cases']:
                        machine.check_case(p, c, case)


if __name__ == '__main__':
    unittest.main()
