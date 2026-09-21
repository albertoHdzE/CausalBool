"""Independent replays of the two final review findings; worker files unchanged."""
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / '.reference')]
import benchmark_optimization as b
import check_optimization_evidence as e

RESULTS = ROOT / 'results/direct_index_v4_optimization_repair2'
BASELINE = ROOT / 'results/direct_index_v4_optimization/baseline'
out = {}
original = e.Checker.require
for label in ['control', 'one_resample', 'missing_verification_stages', 'wrong_seed']:
    def altered(self, path):
        data = original(self, path)
        if path == RESULTS / 'final/runs.json':
            if label == 'one_resample':
                for entry in data['analysis']['ratios'].values():
                    entry['paired_bootstrap_95'] = b.paired_bootstrap(
                        data['runs'], data['analysis']['programs'],
                        entry['baseline_arm'], entry['candidate_arm'], 15,
                        seed=20260920, resamples=1)
            if label == 'wrong_seed':
                data['seed'] = 12345
        if label == 'missing_verification_stages' and path == RESULTS / 'verification/summary.json':
            data['records'] = [r for r in data['records']
                               if r.get('stage') == 'schema' or r.get('step') == 'corpus']
        return data
    with patch.object(e.Checker, 'require', altered):
        result = e.Checker(RESULTS, BASELINE).run()
    out[label] = {'all_passed': result['all_passed'],
                  'failures': [c['check'] for c in result['checks'] if not c['passed']]}
    print(label, out[label], flush=True)
Path(__file__).with_name('probes.json').write_text(json.dumps(out, indent=2) + '\n')
assert out['control']['all_passed']
assert all(not out[k]['all_passed'] for k in out if k != 'control')
