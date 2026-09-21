"""Read-only lead probes of repaired evidence and deadline safeguards."""
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / '.reference')]
import benchmark_optimization as b
import check_optimization_evidence as e
import schema_index as si

RESULTS = ROOT / 'results/direct_index_v4_optimization_repair'
BASELINE = ROOT / 'results/direct_index_v4_optimization/baseline'
out = {}
original = e.Checker.require
for label in ['control', 'drop_extra_corpus', 'erase_hashes',
              'forge_confidence_interval', 'classical_product_drift',
              'one_resample', 'missing_verification_stages']:
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
            if label == 'one_resample':
                for entry in data['analysis']['ratios'].values():
                    entry['paired_bootstrap_95'] = b.paired_bootstrap(
                        data['runs'], data['analysis']['programs'],
                        entry['baseline_arm'], entry['candidate_arm'], 15,
                        seed=20260920, resamples=1)
        if label == 'classical_product_drift' and path == RESULTS / 'comparison/runs.json':
            row = next(r for r in data['runs']
                       if r['arm'] == 'classical' and r['scratch'] % 2 == 0)
            row['cycles'] *= 2
            row['scratch'] //= 2
        if label == 'missing_verification_stages' and path == RESULTS / 'verification/summary.json':
            data['records'] = [r for r in data['records']
                               if r.get('stage') == 'schema' or r.get('step') == 'corpus']
        return data
    with patch.object(e.Checker, 'require', altered):
        result = e.Checker(RESULTS, BASELINE).run()
    out[label] = {'all_passed': result['all_passed'],
                  'failures': [c['check'] for c in result['checks'] if not c['passed']]}
    print(label, out[label], flush=True)

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
    out['expired_final_cover'] = si.solve(expression, 2, meter=meter).to_dict()
Path(__file__).with_name('probes.json').write_text(json.dumps(out, indent=2) + '\n')
print('expired_final_cover', out['expired_final_cover'])
