"""Independent recomputation of this lead run's membership, metrics and speedups."""
import hashlib
import json
import math
from pathlib import Path
import random
import statistics as st

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
data = json.loads((HERE / 'final/runs.json').read_text())
baseline = ROOT / 'results/direct_index_v4_optimization/baseline'
manifest = json.loads((baseline / 'extra_corpus_manifest.json').read_text())
arms = ['classical', 'frozen_bootstrap', 'frozen_full',
        'candidate_bootstrap', 'candidate_full']
public = ['scalar_pipeline', 'scalar_dual_chain', 'vector_axpy', 'vector_bitmix',
          'mixed_broadcast', 'parallel_memory', 'scalar_selects', 'vector_reduction']
evidence = {}
for label, payload, names, repeats in [
    ('public', data, public, 15),
    ('extra', data['extra_corpus'], [p['name'] for p in manifest['programs']], 3)]:
    rows = payload['runs']
    keys = [(r['arm'], r['program'], r['repeat']) for r in rows]
    expected = {(a, p, i) for a in arms for p in names for i in range(repeats)}
    assert len(keys) == len(set(keys)) == len(expected) and set(keys) == expected
    assert not payload['failures']
    assert all(r['correctness'] == 'PASS' and not r.get('leaked')
               and not r.get('discrepancy_count') for r in rows)
    assert all(math.isfinite(r['compile_seconds']) and r['compile_seconds'] > 0
               for r in rows)
    indexed = {(r['arm'], r['program'], r['repeat']): r for r in rows}
    differences = []
    for p in names:
        for i in range(repeats):
            for mode in ['bootstrap', 'full']:
                f, c = indexed['frozen_' + mode, p, i], indexed['candidate_' + mode, p, i]
                if (f['cycles'], f['scratch']) != (c['cycles'], c['scratch']):
                    differences.append([p, i, mode])
    evidence[label] = dict(rows=len(rows), exact_membership=True,
                           candidate_metric_differences=differences)

for name, expected in data['provenance']['source_sha256'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
frozen = hashlib.sha256((baseline / 'snapshot/compiler_frozen.py').read_bytes()).hexdigest()
assert frozen == 'c0574395d339dae3b24e819955795c2a6165953c5966e46062c9bf9b18a50ce2'
evidence['frozen_export_sha256'] = frozen
evidence['speedups'] = {}
for mode in ['bootstrap', 'full']:
    base, cand = 'frozen_' + mode, 'candidate_' + mode
    series = {(arm, p): [next(r['compile_seconds'] for r in data['runs']
              if (r['arm'], r['program'], r['repeat']) == (arm, p, i))
              for i in range(15)] for arm in [base, cand] for p in public}
    gm = lambda xs: math.exp(st.fmean(math.log(x) for x in xs))
    point = gm([st.median(series[base, p]) / st.median(series[cand, p]) for p in public])
    rng = random.Random(20260920)
    draws = []
    for _ in range(10000):
        ratios = []
        for p in public:
            picks = [rng.randrange(15) for _ in range(15)]
            ratios.append(st.median(series[base, p][i] for i in picks) /
                          st.median(series[cand, p][i] for i in picks))
        draws.append(gm(ratios))
    draws.sort()
    evidence['speedups'][mode] = dict(point=point, low=draws[249], high=draws[9750])
(HERE / 'measurement_audit.json').write_text(json.dumps(evidence, indent=2) + '\n')
print(json.dumps(evidence, indent=2))
