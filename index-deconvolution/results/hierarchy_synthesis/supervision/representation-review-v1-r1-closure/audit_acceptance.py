"""Read-only acceptance checks; preserve executor inputs and results."""
import csv
import hashlib
import importlib.util
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
ID = ROOT / 'index-deconvolution'
sys.path[:0] = [str(ID), str(ID / 'experiments')]
from search_v3a.preserve import tree_hash

OUT = Path(__file__).parent
CLOSURE = ID / 'results/hierarchy_synthesis/review_closure/representation-review-v1-r1'
ORIGINAL = ID / 'results/hierarchy_synthesis/representation-review-v1-r1'


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    before = {str(p): tree_hash(p) for p in (CLOSURE, ORIGINAL)}
    pre = read(CLOSURE / 'closure_manifest_pre.json')['hashes']
    post = read(CLOSURE / 'closure_manifest_post.json')['hashes']
    drift = [p for p, h in post.items() if sha(ROOT / p) != h]
    changes = sorted(p for p in set(pre) | set(post) if pre.get(p) != post.get(p))
    script = CLOSURE / 'closure_audit.py'
    checks = {'current_manifest_hashes': not drift,
              'only_disclosed_audit_edit': changes == [str(script.relative_to(ROOT))]}
    spec = importlib.util.spec_from_file_location('reviewed_closure_audit', script)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    # Only redirect this module's output destination; all input paths retain their
    # original values and neither original nor closure result is rewritten.
    audit.HERE = OUT
    try:
        audit.main()
    except SystemExit as e:
        checks['audit_exit_0'] = e.code == 0
    rerun = read(OUT / 'closure_audit_result.json')
    checks['result_reproduces'] = rerun == read(CLOSURE / 'closure_audit_result.json')
    checks['real_data'] = rerun['real_data_pass']
    checks['three_targeted_rejections'] = len(rerun['corruptions']) == 3 and all(
        c['failed_checks'] == [c['intended_check']] and c['rejected_for_intended_reason']
        for c in rerun['corruptions'].values())
    checks['all_data_reads_in_manifest'] = set(rerun['files_read']).issubset(post)
    cases = read(ID / 'protocols/hierarchy_multilevel_v1/CASES.json')['cases']
    checks['raw_inputs_pinned'] = all(post[c['references']['raw']['archive_path']] == c['references']['raw']['archive_sha256'] for c in cases)
    # Supplement the delivered audit's selected-column flat-CSV check with all
    # columns and multiset case coverage, without importing any producer.
    pc = read(ORIGINAL / 'per_case.json')['rows']
    with (ORIGINAL / 'per_case.csv').open() as fh:
        csv_rows = list(csv.DictReader(fh))
    expected = []
    for r in pc:
        R, O = r['R'], r['O']
        vals = [r['case_id'], r['n_bits'], r['a0_bits'], r['a0_info']['codec'], R['mode'],
                R['proposal'], '-'.join(map(str, R['view'])), R['bits'], R['margin_vs_a0_bits'],
                R['margin_vs_a0_per_input_bit'], R['byte_identical_to_a0'], '-'.join(map(str, O['view'])),
                O['bits'], O['margin_vs_a0_bits'], O['byte_identical_to_a0'], r['R_minus_O_bits'],
                R['archive_sha256'], O['archive_sha256'], r['a0_sha256']]
        expected.append(tuple(map(str, vals)))
    checks['complete_flat_csv_multiset'] = Counter(expected) == Counter(tuple(r.values()) for r in csv_rows)
    obs, _, _ = audit.observe()
    raw = [r for r in obs.values() if r['a0_codec'] == 'raw']
    hid = [r for r in obs.values() if r['a0_codec'] != 'raw']
    def margins(rs, tag):
        return [r[tag]['margin_vs_a0_bits'] for r in rs]
    totals = Counter()
    for r in obs.values():
        totals.update(r['R']['component_minus_a0'])
    numeric = {
        'raw_A0_strings': len(raw),
        'raw_A0_families': sorted({r['family'] for r in raw}),
        'raw_A0_best_margin_range': [min(margins(raw, 'R') + margins(raw, 'O')), max(margins(raw, 'R') + margins(raw, 'O'))],
        'raw_A0_median_R_O': [statistics.median(margins(raw, t)) for t in ('R', 'O')],
        'hid_A0_range': [min(margins(hid, 'R') + margins(hid, 'O')), max(margins(hid, 'R') + margins(hid, 'O'))],
        'hid_A0_median_R_O': [statistics.median(margins(hid, t)) for t in ('R', 'O')],
        'R_equal_cases_bits': sorted([[cid, r['R']['bits']] for cid, r in obs.items() if r['R']['margin_vs_a0_bits'] == 0]),
        'R_component_family_sums': {k: sum(v for c, v in totals.items() if c.startswith(k + '.')) for k in ('XFORM', 'PATCH', 'REPEAT', 'AP_UNION', 'SCHEMA_UNION')},
    }
    saved = read(CLOSURE / 'numeric_equality.json')
    checks['eight_prose_numeric_claims'] = all(saved[k]['recomputed'] == v == saved[k]['quoted'] for k, v in numeric.items())
    checks['executor_trees_preserved'] = before == {str(p): tree_hash(p) for p in (CLOSURE, ORIGINAL)}
    out = {'pass': all(checks.values()), 'checks': checks, 'manifest_drift': drift,
           'pre_post_changes': changes, 'manifest_files': len(post), 'data_reads': len(rerun['files_read']),
           'numeric_claims': numeric, 'preserved_trees': before,
           'reviewed_files': {str(p.relative_to(ROOT)): sha(p) for p in (script, CLOSURE / 'closure_manifest.py', CLOSURE / 'numeric_equality.py', CLOSURE / 'SYNTHESIS.md', CLOSURE / 'HANDOFF.md')},
           'scope': 'Artifact-only; no encoders or notebook runs. Original and closure results unchanged.'}
    (OUT / 'audit_acceptance.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({'pass': out['pass'], 'checks': checks}))


if __name__ == '__main__':
    main()
