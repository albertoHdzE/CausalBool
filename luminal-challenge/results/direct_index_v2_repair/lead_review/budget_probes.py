"""Reproduce remaining R4 construction-budget defects without changing production.

Run from luminal-challenge:
  PYTHONPATH=.reference:. python3 results/direct_index_v2_repair/lead_review/budget_probes.py
"""
import json
from pathlib import Path
import direct_constraints as constraints
import direct_contract as contract
import schema_index as schema
from tests_direct.test_constraints import JOINT_FIXTURES, incumbent

source = JOINT_FIXTURES['two_constants']
times, addresses = incumbent(source)
facts = contract.derive(source)
meter = schema.Budget(seconds=10, max_records=533).start()
query = constraints.JointQuery(facts, times, addresses, (0, 1),
                               max(times.values()) + 1,
                               contract.footprint(facts, addresses), meter)
expression = query.expression()
before_solve = meter.records
actual = schema.count_records(expression)
answer = schema.solve(expression, query.n, meter=meter)
expired = schema.Budget(seconds=.1, max_records=1).start()
expired.started -= 1
cover = constraints.relation_cover('le', constraints.constant(0),
                                   constraints.constant(1), 4, expired)
payload = {
    'construction': {'cap': 533, 'meter_records': before_solve,
                     'actual_records': actual, 'construction_returned': True,
                     'solve_status': answer.status, 'records_after_solve': meter.records},
    'expired_constant': {'cover_size': len(cover), 'meter_records': expired.records,
                         'returned_despite_expired_budget': True},
}
Path(__file__).with_suffix('.json').write_text(json.dumps(payload, indent=2) + '\n')
print(json.dumps(payload, indent=2))
