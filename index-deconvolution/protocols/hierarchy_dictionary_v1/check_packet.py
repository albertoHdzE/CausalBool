"""Read-only integrity and consistency gate for the Claude delegation packet."""
import hashlib
import json
import sys
from pathlib import Path

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[2]


def read(p):
    return json.loads(p.read_text())


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def main():
    manifest = read(PACKET / 'DELEGATION_MANIFEST.json')
    state = read(PACKET / 'INITIAL_STATE.json')
    contract = read(PACKET / 'contract.json')
    checks, details, warnings = {}, {}, []
    bad = [p for p, h in manifest['files'].items() if digest(ROOT / p) != h]
    checks['manifest'] = not bad
    details['manifest_mismatches'] = bad
    bad = [p for p, h in state['scientific_dependencies'].items() if digest(ROOT / p) != h]
    checks['scientific_dependencies'] = not bad
    details['scientific_mismatches'] = bad
    drift = [p for p, h in state['protected_files'].items() if digest(ROOT / p) != h]
    allowed = set(state['external_drift_warning_only'])
    checks['protected_files'] = not (set(drift) - allowed)
    warnings.extend('External drift; record provenance, never restore: ' + p for p in drift if p in allowed)
    details['protected_drift'] = drift
    cases = read(ROOT / contract['cases_path'])['cases']
    expected = {(f'F{i:02}', n, rep, ragged) for i in range(1, 13)
                for n in (1024, 4096) for rep in (3000, 3001) for ragged in (False, True)}
    checks['cases'] = len(cases) == 96 and {(c['family'], c['base_length'], c['replicate'], c['ragged']) for c in cases} == expected
    checks['actual_lengths'] = all(c['n_bits'] == c['base_length'] + (3 if c['ragged'] else 0) for c in cases)
    checks['jobs'] = contract['counts']['baseline_jobs'] == 96 and contract['counts']['augmentation_jobs'] == 288 and contract['counts']['new_jobs'] == 384
    checks['arms_nested'] = contract['arms'] == {'A0': ['k1'], 'D0': ['O'], 'D1': ['O', 'P'], 'D2': ['O', 'P', 'R(O)', 'R(P)']}
    checks['view_and_request_caps'] = len(contract['widths']) * 2 * contract['levels'] == 64 and 64 * 4 * 4 == contract['limits']['full_root_requests']
    checks['resources'] = sum(contract['resources']['category_caps_s'].values()) == contract['resources']['total_s'] == 21600
    checks['no_branch_pruning'] = contract['prune_saturated'] is False and contract['prune_single_symbol'] is False
    checks['no_inference'] = contract['exposed_data'] is True and contract['bootstrap_draws'] == 0
    checks['relation_limits'] = (contract['limits']['predecessors'], contract['limits']['relation_flips'], contract['limits']['relation_hops'], contract['relation_flags']) == (8, 8, 8, [0, 1, 2, 3])
    archive_checks = {}
    bad = []
    records = 0
    for c in cases:
        if digest(ROOT / c['source_rows_path']) != c['source_rows_sha256']:
            bad.append(c['case_id'] + ': source rows')
        for r in c['references'].values():
            p = r['archive_path']
            if p not in archive_checks:
                q = ROOT / p
                archive_checks[p] = (digest(q), q.stat().st_size * 8 if q.is_file() else None)
            if archive_checks[p] != (r['archive_sha256'], r['archive_bits']):
                bad.append(c['case_id'] + ': ' + p)
            records += 1
    checks['reference_bytes'] = not bad
    details['reference_mismatches'] = bad
    previous = read(PACKET / 'PREVIOUS_A3.json')['records']
    bad = []
    for r in previous:
        if digest(ROOT / r['row_path']) != r['row_sha256'] or digest(ROOT / r['archive_path']) != r['archive_sha256'] or digest(ROOT / r['trace_path']) != r['trace_sha256']:
            bad.append(r['case_id'])
    checks['previous_A3'] = len(previous) == 96 and {r['case_id'] for r in previous} == {c['case_id'] for c in cases} and not bad
    details['previous_A3_mismatches'] = bad
    out = {'all_pass': all(checks.values()), 'checks': checks, 'details': details,
           'warnings': warnings, 'reference_records': records,
           'distinct_reference_archives_hashed': len(archive_checks),
           'note': 'No encoder runs. Executor must separately capture full prior-tree preservation before edits.'}
    print(json.dumps(out, indent=2))
    return 0 if out['all_pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
