"""Isolate historical-control exit behavior using complete acceptance replays."""
import argparse
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / '.reference')]
import benchmark_optimization as b

RESULTS = ROOT / 'results/direct_index_v4_optimization_repair'
BASELINE = ROOT / 'results/direct_index_v4_optimization/baseline'
data = json.loads((RESULTS / 'final/runs.json').read_text())
out = {}
for drift in [False, True]:
    rows = copy.deepcopy(data['runs'])
    if drift:
        for row in rows:
            if row['arm'] == 'classical' and row['scratch'] % 2 == 0:
                row['cycles'] *= 2
                row['scratch'] //= 2
    with tempfile.TemporaryDirectory() as temp:
        args = argparse.Namespace(output=temp, baseline=str(BASELINE),
            allow_existing=False, timeout=20.0, seed=20260920, repeats=15,
            quiet=True, skip_extra_corpus=False, diagnostic=False, extra_repeats=3)
        with patch.object(b.Bench, 'run', side_effect=[(rows, [], []),
                          (data['extra_corpus']['runs'], [], [])]), \
             patch.object(b, 'paired_bootstrap', return_value={'low': 1, 'high': 1}), \
             contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            code = b.phase_final(args)
        written = json.loads((Path(temp) / 'runs.json').read_text())
        out['drift' if drift else 'control'] = {
            'exit': code,
            'failed_gates': [k for k, v in written['acceptance_gates'].items() if not v['passed']]}
Path(__file__).with_suffix('.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps(out, indent=2))
