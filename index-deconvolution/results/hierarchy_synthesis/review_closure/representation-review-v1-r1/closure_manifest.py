"""Supplemental closure input manifest for representation-review-v1-r1 (review R2).

Usage (from index-deconvolution/): python closure_manifest.py pre|post|compare

Hashes every file the closure audit depends on, created at closure time
(2026-10-04). It does NOT replace or backdate the original
`evidence_manifest_{pre,post}.json`, which were written before the synthesis
ran and omitted the 96 raw input archives; those files are hashed here as
evidence, never edited. Raw archives are additionally compared with the
`archive_sha256` commitments pinned in CASES.json.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
ID = ROOT / 'index-deconvolution'
RUN = ID / 'results/hierarchy_synthesis/representation-review-v1-r1'
SUP = ID / 'results/hierarchy_synthesis/supervision/representation-review-v1-r1'
D = ID / 'results/hierarchy_dictionary_v1/dictionary-feasibility-v1-r1'
CASES = ID / 'protocols/hierarchy_multilevel_v1/CASES.json'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def inventory():
    groups = {}
    cases = json.loads(CASES.read_text())['cases']
    groups['protocol'] = [CASES]
    groups['raw_input_archives'] = [ROOT / c['references']['raw']['archive_path'] for c in cases]
    groups['original_synthesis_run'] = sorted(p for p in RUN.rglob('*') if p.is_file())
    groups['reviewer_instructions_and_supervisor_audit'] = sorted(p for p in SUP.rglob('*') if p.is_file())
    rows, traces, archives = [], [], []
    for c in cases:
        for arm in ('A0', 'D2'):
            p = D / 'rows' / f"{c['case_id']}.{arm}.json"
            rows.append(p)
            r = json.loads(p.read_text())
            if arm == 'A0':
                archives.append(D / r['archive_path'])
            else:
                traces.append(D / r['trace_path'])
    for r in json.loads((RUN / 'per_case.json').read_text())['rows']:
        for tag in ('R', 'O'):
            h = r[tag]['archive_sha256']
            archives.append(D / 'archives' / h[:2] / f'{h}.isd')
    groups['dictionary_rows'] = rows
    groups['dictionary_traces'] = traces
    groups['archives_read'] = sorted(set(archives))
    groups['owner_sources'] = sorted((ID / 'hierarchy').glob('*.py'))
    groups['closure_audit_scripts'] = [HERE / 'closure_audit.py', HERE / 'closure_manifest.py']
    pinned = {str((ROOT / c['references']['raw']['archive_path']).relative_to(ROOT)):
              c['references']['raw']['archive_sha256'] for c in cases}
    return groups, pinned


def main(stage):
    if stage == 'compare':
        a = json.loads((HERE / 'closure_manifest_pre.json').read_text())['hashes']
        b = json.loads((HERE / 'closure_manifest_post.json').read_text())['hashes']
        out = {'n_pre': len(a), 'n_post': len(b), 'changed': sorted(k for k in a if b.get(k) != a[k]),
               'added': sorted(set(b) - set(a))}
        out['identical'] = not out['changed'] and not out['added']
        (HERE / 'closure_manifest_compare.json').write_text(json.dumps(out, indent=2) + '\n')
        print(json.dumps(out))
        return
    groups, pinned = inventory()
    hashes, missing, by_group = {}, [], {}
    for g, paths in groups.items():
        by_group[g] = []
        for p in paths:
            k = str(p.relative_to(ROOT))
            by_group[g].append(k)
            if p.exists():
                hashes[k] = sha(p)
            else:
                missing.append(k)
    raw_vs_pinned = {k: hashes.get(k) == v for k, v in pinned.items()}
    old = json.loads((RUN / 'evidence_manifest_post.json').read_text())['hashes']
    old_keys = {(k if k.startswith('index-deconvolution/') else 'index-deconvolution/' + k) for k in old}
    out = {'stage': stage, 'created_by': 'closure (2026-10-04); supplemental, not a pre-synthesis record',
           'n_files': len(hashes), 'missing': missing, 'group_counts': {g: len(v) for g, v in by_group.items()},
           'raw_archives_match_CASES_pins': sum(raw_vs_pinned.values()), 'raw_archives_total': len(raw_vs_pinned),
           'raw_archives_absent_from_original_manifest': sum(k not in old_keys for k in pinned),
           'groups': by_group, 'hashes': hashes}
    (HERE / f'closure_manifest_{stage}.json').write_text(json.dumps(out, indent=1, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k not in ('groups', 'hashes')}))


if __name__ == '__main__':
    main(sys.argv[1])
