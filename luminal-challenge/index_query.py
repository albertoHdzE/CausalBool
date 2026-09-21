"""Finite-domain constraints over CausalBool decimal-anchor/sumandos programs.

This adapter reuses Doppel's existing shared decision program. Its backend is
an ordered binary decision diagram (BDD), not a newly claimed SAT algorithm.
Local predicates are built over their supports; no full joint table is built.
"""
from dataclasses import dataclass
import importlib.util
from itertools import product
from pathlib import Path
import sys
import time

SOURCE = Path(__file__).resolve().parents[1] / 'doppel-challenge/src/doppel_challenge/repertoire_program.py'
spec = importlib.util.spec_from_file_location('_luminal_repertoire_program', SOURCE)
rp = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rp
spec.loader.exec_module(rp)


@dataclass
class Factor:
    scope: tuple
    predicate: object
    label: str


class ConstraintQuery:
    def __init__(self, domains):
        self.domains = {name: tuple(values) for name, values in domains.items()}
        if any(not values for values in self.domains.values()):
            raise ValueError('empty domain')
        self.coordinates = {}
        position = 0
        for name, values in self.domains.items():
            if len(set(values)) != len(values):
                raise ValueError('duplicate domain value')
            width = (len(values) - 1).bit_length()
            self.coordinates[name] = tuple(range(position, position + width))
            position += width
        self.n = max(position, 1)
        self.factors = []

    def add(self, scope, predicate, label):
        scope = tuple(dict.fromkeys(scope))
        if any(name not in self.domains for name in scope):
            raise ValueError('unknown variable')
        self.factors.append(Factor(scope, predicate, label))

    def accepts(self, assignment):
        return (set(assignment) == set(self.domains)
                and all(value in self.domains[name] for name, value in assignment.items())
                and all(f.predicate(*(assignment[name] for name in f.scope)) for f in self.factors))

    def decode(self, anchor):
        answer = {}
        for name, coords in self.coordinates.items():
            code = sum(((anchor >> coord) & 1) << j for j, coord in enumerate(coords))
            if code >= len(self.domains[name]):
                raise ValueError('index contains an invalid domain code')
            answer[name] = self.domains[name][code]
        return answer

    def solve_index(self, seconds=0.25, max_nodes=30000):
        start = time.perf_counter()
        manager = rp._Manager(self.n, rp.ProgramLimits(max_nodes=max_nodes, timeout_seconds=seconds))
        root = 1
        evaluations = 0
        try:
            # Codes beyond a non-power-of-two domain must never become sumandos.
            factors = [Factor((name,), lambda value: True, 'domain') for name in self.domains]
            factors += self.factors
            for factor in factors:
                coordinates = sorted(c for name in factor.scope for c in self.coordinates[name])
                chosen = {}

                def build(depth):
                    nonlocal evaluations
                    manager.check()
                    if depth == len(coordinates):
                        values = []
                        for name in factor.scope:
                            code = sum(chosen[c] << j for j, c in enumerate(self.coordinates[name]))
                            if code >= len(self.domains[name]):
                                return 0
                            values.append(self.domains[name][code])
                        evaluations += 1
                        return int(bool(factor.predicate(*values)))
                    coordinate = coordinates[depth]
                    chosen[coordinate] = 0
                    low = build(depth + 1)
                    chosen[coordinate] = 1
                    high = build(depth + 1)
                    return manager.mk(coordinate, low, high)

                root = manager.apply('and', root, build(0))
                if root == 0:
                    break
            built = time.perf_counter()
            anchor, fixed, ref = 0, 0, root
            while ref >= 2:
                v, low, high = manager.nodes[ref - 2]
                fixed |= 1 << v
                if low:
                    ref = low
                else:
                    anchor |= 1 << v
                    ref = high
            answer = self.decode(anchor) if root else None
            retrieved = time.perf_counter()
            # Adapter uses one Boolean result, padded with constant zero columns
            # only because the existing codec expects n ordered output references.
            compiled = manager.finish([root] + [0] * (self.n - 1))
            reachable = len(compiled.nodes)
            rw = (reachable + 1).bit_length()
            logical_bits = (2 * (reachable + 1).bit_length() - 1
                            + reachable * ((self.n - 1).bit_length() + 2 * rw) + rw)
            report = dict(status='SAT' if root else 'UNSAT',
                          build_seconds=built-start, retrieval_seconds=retrieved-built,
                          total_seconds=time.perf_counter()-start,
                          allocated_nodes=len(manager.nodes), reachable_nodes=reachable,
                          boolean_variables=self.n, local_predicate_evaluations=evaluations,
                          one_output_decision_bits=logical_bits,
                          truth_table_bits=1 << self.n,
                          assignment_count=__import__('math').prod(map(len, self.domains.values())))
            if root:
                report.update(decimal_anchor=anchor, free_mask=((1 << self.n)-1) ^ fixed)
                check_start = time.perf_counter()
                if not self.accepts(answer):
                    raise AssertionError('symbolic witness violates original predicates')
                report['witness_check_seconds'] = time.perf_counter()-check_start
                report['total_seconds'] = time.perf_counter()-start
                return answer, report
            return None, report
        except (TimeoutError, rp.ResourceLimitError) as exc:
            return None, dict(status='UNKNOWN', reason=str(exc),
                              total_seconds=time.perf_counter()-start,
                              allocated_nodes=len(manager.nodes), boolean_variables=self.n,
                              local_predicate_evaluations=evaluations)

    def solve_exhaustive(self, seconds=0.25):
        start = time.perf_counter()
        examined = 0
        # Match the symbolic traversal's low-first, LSB-first coordinate order.
        ordered = []
        for name, values in self.domains.items():
            width = len(self.coordinates[name])
            codes = sorted(range(len(values)), key=lambda c: tuple((c >> j) & 1 for j in range(width)))
            ordered.append(tuple(values[c] for c in codes))
        for values in product(*ordered):
            if time.perf_counter() - start > seconds:
                return None, dict(status='UNKNOWN', examined=examined,
                                  total_seconds=time.perf_counter()-start)
            examined += 1
            answer = dict(zip(self.domains, values))
            if self.accepts(answer):
                return answer, dict(status='SAT', examined=examined,
                                    total_seconds=time.perf_counter()-start)
        return None, dict(status='UNSAT', examined=examined,
                          total_seconds=time.perf_counter()-start)
