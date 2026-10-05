"""Supervisor read-only audit; never launches encoders or writes the study run."""
import hashlib
import json
import statistics
import sys
import tarfile
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
ID = ROOT / 'index-deconvolution'
sys.path[:0] = [str(ID / 'experiments'), str(ID), str(ROOT / 'src')]
from hierarchy_multilevel.audit import audit
from search_v3a.preserve import tree_hash

RUN = ID / 'results/hierarchy_multilevel_v1/multilevel-feasibility-v1-r1'
OUT = Path(__file__).parent

def read(p):
    return json.loads(p.read_text())

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def strip(v):
    if isinstance(v, dict):
        return {k: strip(x) for k, x in v.items() if not k.endswith('wall_s')}
    if isinstance(v, list):
        return [strip(x) for x in v]
    return v

def main():
    start = time.monotonic()
    before = tree_hash(RUN)
    checks = {}
    lock = read(RUN / 'implementation_lock.json')
    checks['lock_hash'] = sha(RUN / 'implementation_lock.json') == (RUN / 'implementation_lock.sha256').read_text().strip()
    checks['all_locked_members_current'] = all(sha(ROOT / p) == h for p, h in lock['members'].items())
    checks['snapshot_hash'] = sha(RUN / 'source_snapshot.tar') == lock['snapshot_sha256']
    with tarfile.open(RUN / 'source_snapshot.tar') as tf:
        checks['snapshot_members'] = set(tf.getnames()) == set(lock['members'])
        checks['snapshot_contents'] = all(hashlib.sha256(tf.extractfile(p).read()).hexdigest() == h for p, h in lock['members'].items())
    initial = read(RUN / 'preservation/initial_preservation.json')
    final = read(RUN / 'preservation/final_preservation.json')
    for group in ('hierarchy_sources', 'shared_owners'):
        checks[group] = initial[group] == final[group] and all(sha(ROOT / p) == h for p, h in initial[group].items())
    checks['protected_notebooks'] = all(sha(ROOT / p) == v['now'] == v['packet'] for p, v in initial['protected_notebooks'].items())
    trees = {p: tree_hash(ROOT / p) for p in initial['old_result_trees']}
    checks['old_trees'] = trees == initial['old_result_trees'] == final['old_result_trees']
    checks['bitacora'] = tree_hash(ID / 'bitacora') == initial['bitacora'] == final['bitacora']
    checks['notebook_readme'] = sha(ID / 'notebooks/README.md') == initial['notebook_readme_sha256']
    arithmetic = audit(RUN)
    checks['archive_arithmetic'] = arithmetic['pass']
    cases = read(ID / 'protocols/hierarchy_multilevel_v1/CASES.json')['cases']
    fields = read(ID / 'protocols/hierarchy_multilevel_v1/contract.json')['baseline_reproduction_fields']
    statuses = Counter()
    view_statuses = Counter()
    proposal_statuses = Counter()
    excess = []
    bad = []
    for c in cases:
        cid = c['case_id']
        oldpath = ROOT / c['source_rows_path']
        if sha(oldpath) != c['source_rows_sha256']:
            bad.append(cid + ': saved rows hash')
        old = read(oldpath)
        if isinstance(old, dict):
            old = old.get('rows', old)
        old = next(r for r in old if r['method'] == 'hid_full')
        a0 = read(RUN / 'rows' / (cid + '.A0.json'))
        for f in fields:
            key = 'search_counters' if f.startswith('search_counters ') else f
            if strip(old.get(key)) != strip(a0.get(key)):
                bad.append(cid + ': ' + key)
        for arm in ('A1', 'A2', 'A3'):
            row = read(RUN / 'rows' / (cid + '.' + arm + '.json'))
            statuses[row['status']] += 1
            if row['archive_sha256'] != a0['archive_sha256']:
                bad.append(cid + ': composite bytes')
            if sha(RUN / row['trace_path']) != row['trace_sha256']:
                bad.append(cid + ': trace hash')
            tr = read(RUN / row['trace_path'])
            if arm == 'A3':
                candidates = []
                for v in tr['views']:
                    view_statuses[v['status']] += 1
                    for p in v['proposals']:
                        proposal_statuses[p['status']] += 1
                        if p['archive_bits'] is not None:
                            candidates.append(p['archive_bits'])
                excess.append((min(candidates) - a0['archive_bits']) / a0['archive_bits'])
    checks['baseline_fields_composites_traces'] = not bad
    checks['all_augmentation_ok'] = statuses == {'ok': 288}
    checks['no_view_or_request_caps'] = not any('CAP' in k for k in view_statuses) and not any('CAP' in k for k in proposal_statuses)
    nb = read(RUN / 'notebook/run2.checks.json')
    checks['notebook_saved_checks'] = all(nb['checks'].values())
    checks['notebook_driver_hash'] = sha(ID / 'experiments/hierarchy_multilevel/notebook21.py') == nb['driver_sha256']
    checks['notebook_builder_hash'] = sha(ID / 'notebooks/build_21.py') == nb['builder_sha256']
    checks['run_preserved'] = tree_hash(RUN) == before
    out = {'pass': all(checks.values()), 'checks': checks, 'problems': bad,
           'arithmetic': arithmetic, 'old_trees': trees, 'run_tree': before,
           'locked_members': len(lock['members']), 'closure_files': len(lock['closure']),
           'a3_view_statuses': dict(view_statuses), 'a3_proposal_statuses': dict(proposal_statuses),
           'median_best_proposal_relative_excess': statistics.median(excess),
           'audit_wall_s': time.monotonic() - start,
           'scope': 'No new encoder jobs; stored notebook evidence reviewed, not re-executed.'}
    (OUT / 'audit_review.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({k: out[k] for k in ('pass', 'checks', 'problems', 'audit_wall_s')}))
    return 0 if out['pass'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
