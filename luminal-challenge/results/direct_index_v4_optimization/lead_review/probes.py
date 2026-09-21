"""Lead rejection probes; no production files or worker evidence are modified."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / '.reference')]
import benchmark_optimization as b
import check_optimization_evidence as e
import schema_index as si

RESULTS = ROOT / 'results/direct_index_v4_optimization'
out = {}
original = e.Checker.require
for label in ['control', 'drop_extra_corpus', 'erase_hashes',
              'forge_confidence_interval', 'classical_product_drift']:
    def altered(self, path):
        data = original(self, path)
        if path == RESULTS / 'final/runs.json':
            if label == 'drop_extra_corpus':
                data['extra_corpus'] = None
            if label == 'erase_hashes':
                data['provenance']['source_sha256'] = {}
                data['provenance']['test_sha256'] = {}
            if label == 'forge_confidence_interval':
                for entry in data['analysis']['ratios'].values():
                    entry['paired_bootstrap_95'].update(low=999, high=1000)
        if label == 'classical_product_drift' and path == RESULTS / 'comparison/runs.json':
            row = next(r for r in data['runs']
                       if r['arm'] == 'classical' and r['scratch'] % 2 == 0)
            row['cycles'] *= 2
            row['scratch'] //= 2
        return data
    with patch.object(e.Checker, 'require', altered):
        out[label] = e.Checker(RESULTS).run()['all_passed']

# Replaying real measurements through the actual phase return path should reject
# a product-preserving change in historical classical metrics.
payload = json.loads((RESULTS / 'final/runs.json').read_text())
for row in payload['runs']:
    if row['arm'] == 'classical' and row['scratch'] % 2 == 0:
        row['cycles'] *= 2
        row['scratch'] //= 2
with tempfile.TemporaryDirectory() as temp:
    args = argparse.Namespace(output=temp, baseline=str(RESULTS / 'baseline'),
        allow_existing=False, timeout=20.0, seed=20260920, repeats=15,
        quiet=True, skip_extra_corpus=True)
    # Interval generation is irrelevant to this integer-control rejection probe.
    with patch.object(b.Bench, 'run', return_value=(payload['runs'], [], [])), \
         patch.object(b, 'paired_bootstrap', return_value={'low': 1, 'high': 1}), \
         contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()):
        out['phase_final_classical_drift_exit'] = b.phase_final(args)
    measured = json.loads((Path(temp) / 'runs.json').read_text())
    gate = measured['analysis']['frozen_classical_integers']
    out['phase_final_drift_gate'] = {
        'passed': gate['passed'], 'checked': gate['checked'],
        'drift_count': len(gate['drift']), 'detail': gate['detail']}

# Deterministic clock injection at the final conflicting cover. The clock passes
# the deadline after the batch's initial check, simulating time spent scanning
# that cover. There must be a post-scan/final verdict check.
clock = [0.0]
with patch.object(si.time, 'monotonic', side_effect=lambda: clock[0]):
    meter = si.Budget(seconds=1.0).start()
    expression = si.AllOf((si.Leaf((si.Cube(2, 0, 0),)),
                           si.Leaf((si.Cube(2, 1, 0), si.Cube(2, 2, 0)))))
    intersection = meter.intersection
    def advancing_intersection(count=1):
        intersection(count)
        if count == 2:
            clock[0] = 2.0
    meter.intersection = advancing_intersection
    result = si.solve(expression, 2, meter=meter)
    out['expired_final_cover'] = result.to_dict()

destination = Path(__file__).with_name('probes.json')
destination.write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps(out, indent=2))
