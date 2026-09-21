"""Independently check repaired-run provenance, membership and integer controls."""
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
import compare_direct as comparison

protected = comparison.verify_protected()
commit = comparison.verify_reference()
export_hash = comparison.verify_export_fresh()
verification = json.loads((HERE / 'verification/summary.json').read_text())
for name, expected in verification['source_sha256'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
for name, expected in verification['test_sha256'].items():
    assert hashlib.sha256((ROOT / 'tests_direct' / name).read_bytes()).hexdigest() == expected, name
measured = json.loads((HERE / 'comparison/runs.json').read_text())
assert not measured['failures']
assert measured['export_sha256'] == export_hash == verification['export']['sha256']
programs = {json.loads(p.read_text())['name'] for p in (ROOT / '.reference/programs').glob('*.json')}
expected_keys = {(arm, p, repeat) for arm in comparison.ARMS for p in programs for repeat in range(3)}
rows = {(r['arm'],r['program'],r['repeat']):r for r in measured['runs']}
assert len(rows) == len(measured['runs']) == 72 and set(rows) == expected_keys
historical = json.loads((ROOT / 'results/comparison.json').read_text())
for p in historical['programs']:
    for arm in ('serial','classical'):
        for repeat in range(3):
            actual = rows[arm,p['program'],repeat]
            old = p['runs'][arm][repeat]
            assert (actual['cycles'],actual['scratch']) == (old['cycles'],old['scratch'])
scores = {}
for arm in comparison.ARMS:
    scores[arm] = []
    for repeat in range(3):
        score = math.exp(statistics.fmean(
            math.log((rows['serial',p,repeat]['cycles'] * rows['serial',p,repeat]['scratch']) /
                     (rows[arm,p,repeat]['cycles'] * rows[arm,p,repeat]['scratch'])) / 2
            for p in programs))
        scores[arm].append(score)
        if arm == 'direct_index':
            assert score > 1
corpus = json.loads((HERE / 'verification/isolated_corpus.json').read_text())
assert corpus['programs'] == corpus['passed'] == 142 and not corpus['failures']
assert corpus['cases'] == 277
payload = {'evidence_checks':'PASS', 'release_verdict':'CHANGES_REQUIRED',
           'reference_commit':commit,'protected_sha256':protected,'export_sha256':export_hash,
           'exact_run_membership':True,'historical_integer_metrics_match':True,
           'independently_recomputed_scores':scores,'timings':measured['summary'],
           'corpus_max_process_seconds':corpus['max_process_seconds'],
           'corpus_accepted_improvements':corpus['accepted_improvements']}
(HERE / 'evidence_checks.json').write_text(json.dumps(payload,indent=2)+'\n')
print(json.dumps(payload,indent=2))
