"""Read-only supervisor verification; output only to this supervision directory."""
import hashlib
import json
import sys
import tarfile
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
ID = ROOT / 'index-deconvolution'
sys.path[:0] = [str(ID / 'experiments'), str(ID), str(ROOT / 'src')]
from hierarchy_dictionary.audit import audit
from search_v3a.preserve import tree_hash

RUN = ID / 'results/hierarchy_dictionary_v1/dictionary-feasibility-v1-r1'


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
    checks['lock_hash'] = sha(RUN / 'implementation_lock.json') == '19b53d32873a37cfd37e84129d880056ebf6132a6994c2f6e339f25142373780'
    checks['closure'] = all(sha(ROOT / p) == h for p, h in lock['closure'].items())
    checks['snapshot_hash'] = sha(RUN / 'source_snapshot.tar') == lock['snapshot_sha256']
    with tarfile.open(RUN / 'source_snapshot.tar') as tf:
        checks['snapshot_members'] = set(tf.getnames()) == set(lock['closure'])
        checks['snapshot_contents'] = all(hashlib.sha256(tf.extractfile(p).read()).hexdigest() == h for p, h in lock['closure'].items())
    initial = read(RUN / 'preservation/initial.json')
    final = read(RUN / 'preservation/final.json')
    for group in ('hierarchy_sources', 'multilevel_package'):
        checks[group] = initial[group] == final[group] and all(sha(ROOT / p) == h for p, h in initial[group].items())
    checks['scientific_dependencies'] = initial['scientific_dependencies'] == final['scientific_dependencies'] and all(sha(ROOT / p) == v['now'] == v['packet'] for p, v in initial['scientific_dependencies'].items())
    checks['protected_files_at_handoff'] = initial['protected_files'] == final['protected_files'] and all(v['now'] == v['packet'] for v in initial['protected_files'].values())
    drift = {p: {'recorded': v['now'], 'current': sha(ROOT / p)} for p, v in initial['protected_files'].items() if sha(ROOT / p) != v['now']}
    permitted = read(ID / 'protocols/hierarchy_dictionary_v1/INITIAL_STATE.json')['external_drift_warning_only']
    checks['current_protected_drift_within_explicit_allowlist'] = set(drift).issubset(permitted)
    trees = {p: tree_hash(ROOT / p) for p in initial['prior_result_trees']}
    checks['prior_trees'] = trees == initial['prior_result_trees'] == final['prior_result_trees']
    checks['protocols'] = tree_hash(ID / 'protocols') == initial['protocols_tree'] == final['protocols_tree']
    checks['bitacora'] = tree_hash(ID / 'bitacora') == initial['bitacora'] == final['bitacora']
    arithmetic = audit(RUN)
    checks['archive_arithmetic'] = arithmetic['pass']
    cases = read(ID / 'protocols/hierarchy_multilevel_v1/CASES.json')['cases']
    fields = read(ID / 'protocols/hierarchy_multilevel_v1/contract.json')['baseline_reproduction_fields']
    view_status = Counter()
    comparisons = {m: Counter() for m in ('P', 'R(O)', 'R(P)')}
    hop_reject = Counter()
    ties = set()
    bad = []
    statuses = Counter()
    for c in cases:
        cid = c['case_id']
        path = ROOT / c['source_rows_path']
        if sha(path) != c['source_rows_sha256']:
            bad.append(cid + ': source row hash')
        old = read(path)
        if isinstance(old, dict):
            old = old.get('rows', old)
        old = next(r for r in old if r['method'] == 'hid_full')
        a0 = read(RUN / 'rows' / (cid + '.A0.json'))
        for field in fields:
            k = 'search_counters' if field.startswith('search_counters ') else field
            if strip(old.get(k)) != strip(a0.get(k)):
                bad.append(cid + ': baseline ' + k)
        for arm in ('D0', 'D1', 'D2'):
            row = read(RUN / 'rows' / (cid + '.' + arm + '.json'))
            statuses[row['status']] += 1
            if row['archive_sha256'] != a0['archive_sha256'] or row['stop_reason'] != 'completed':
                bad.append(cid + ': output or completion')
            if arm != 'D2':
                continue
            tr = read(RUN / row['trace_path'])
            for v in tr['views']:
                view_status[v['status']] += 1
                modes = {m['mode']: m for m in v.get('modes', [])}
                if not modes:
                    continue
                for name, m in modes.items():
                    p = RUN / 'archives' / m['best_sha256'][:2] / (m['best_sha256'] + '.isd')
                    if p.stat().st_size * 8 != m['best_bits']:
                        bad.append(cid + ': mode archive length')
                    if m['best_bits'] < a0['archive_bits']:
                        bad.append(cid + ': shorter unselected candidate')
                    if name != 'O':
                        delta = m['best_bits'] - modes['O']['best_bits']
                        comparisons[name]['better' if delta < 0 else 'worse' if delta > 0 else 'tie'] += 1
                    if name.startswith('R('):
                        meta = m['construction']
                        counts = meta['comparison_flip_counts']
                        if isinstance(counts, str):
                            counts = modes['R(O)']['construction']['comparison_flip_counts']
                        nrej = sum(q <= 8 and meta['hops'][meta['comparisons_first_j'][i] + z // 4] >= 8
                                   for i, qs in enumerate(counts) for z, q in enumerate(qs))
                        if nrej != meta['eligible_by_flips_rejected_by_hop_cap']:
                            bad.append(cid + ': hop rejection count')
                        hop_reject[name] += nrej
                        if c['family'] == 'F10' and m['best_bits'] == a0['archive_bits'] and m['best_sha256'] != a0['archive_sha256']:
                            ties.add(cid)
    checks['baseline_composites_candidates_hop_counts'] = not bad
    checks['all_jobs_complete'] = statuses == {'ok': 288}
    checks['view_counts'] = view_status == {'EVALUATED': 6096, 'INELIGIBLE_SHORT': 48}
    checks['view_gains'] = comparisons['R(O)'] == {'better': 1243, 'tie': 2628, 'worse': 2225} and comparisons['P'] == {'better': 368, 'tie': 4787, 'worse': 941}
    checks['F10_distinct_ties'] = len(ties) == 4
    nb = read(RUN / 'notebook/run3.checks.json')
    checks['saved_notebook_checks'] = all(nb['checks'].values())
    checks['notebook_builder_driver'] = (sha(ID / 'notebooks/build_22.py') == nb['builder_sha256'] and sha(ID / 'experiments/hierarchy_dictionary/notebook22.py') == nb['driver_sha256'])
    checks['delivered_notebook'] = sha(ID / 'notebooks/22_hierarchy_dictionary.ipynb') == sha(RUN / 'notebook/run3.notebook_dir.ipynb')
    checks['run_preserved'] = tree_hash(RUN) == before
    out = {'pass': all(checks.values()), 'checks': checks, 'problems': bad,
           'arithmetic': arithmetic, 'prior_trees': trees, 'run_tree': before,
           'current_external_drift_warning': drift,
           'mode_comparisons': {k: dict(v) for k, v in comparisons.items()},
           'hop_rejections_per_mode': dict(hop_reject), 'F10_distinct_ties': sorted(ties),
           'audit_wall_s': time.monotonic() - start,
           'scope': 'No encoder jobs or notebook re-execution; saved guard evidence reviewed.'}
    (Path(__file__).parent / 'audit_review.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({k: out[k] for k in ('pass', 'checks', 'problems', 'audit_wall_s')}))
    return 0 if out['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
