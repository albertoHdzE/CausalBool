"""Replay real worker results through run_all to probe its release gates.

Run from luminal-challenge:
  python3 results/direct_index_v3_repair/lead_review/gate_probes.py

Only subprocess results are injected; run_all recomputes every aggregate.
No production files, protected inputs, or old evidence are changed.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
import compare_direct as comparison

source = json.loads((HERE.parent / 'comparison/runs.json').read_text())
outputs = []
original_run = subprocess.run

for scenario in ('control', 'duplicate_classical_measurement', 'classical_product_preserved_drift'):
    counter = [0]

    def replay(argv, **kwargs):
        if argv[0] != sys.executable:
            return original_run(argv, **kwargs)
        repeat = (counter[0] // 3) % 3
        counter[0] += 1
        arm = argv[argv.index('--worker') + 1] if '--worker' in argv else 'direct_index'
        program = json.loads(Path(argv[-1]).read_text())['name']
        record = copy.deepcopy(next(r for r in source['runs'] if
                                    r['arm'] == arm and r['program'] == program
                                    and r['repeat'] == repeat))
        if scenario == 'duplicate_classical_measurement' and arm == 'classical' and repeat == 1:
            first = json.loads(sorted((ROOT / '.reference/programs').glob('*.json'))[0].read_text())['name']
            if program == first:
                record = copy.deepcopy(next(r for r in source['runs'] if
                                            r['arm'] == arm and r['repeat'] == repeat
                                            and r['program'] != program))
        if scenario == 'classical_product_preserved_drift' and arm == 'classical':
            if record['scratch'] % 2 == 0:
                record['cycles'] *= 2
                record['scratch'] //= 2
        return subprocess.CompletedProcess(argv, 0, json.dumps(record), '')

    with patch.object(comparison.subprocess, 'run', side_effect=replay):
        result = comparison.run_all(3, 20)
    outputs.append({'scenario': scenario, 'gates': result['gates'],
                    'classical_repetitions': result['per_repeat']['classical'],
                    'run_count': len(result['runs']),
                    'unique_run_keys': len({(r['arm'],r['program'],r['repeat']) for r in result['runs']})})

(HERE / 'gate_probes.json').write_text(json.dumps(outputs, indent=2) + '\n')
for result in outputs:
    print(result['scenario'], 'all_passed=',result['gates']['all_passed']['passed'],
          'unique=',result['unique_run_keys'], 'classical_repeats=',len(result['classical_repetitions']))
