"""Supervisor artifact audit, independent of synthesis analysis.py and audit.py."""
import hashlib
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
ID = ROOT / 'index-deconvolution'
sys.path[:0] = [str(ID), str(ID / 'experiments')]
from hierarchy.decode import decode_archive
from hierarchy.ledger import archive_ledger
from hierarchy.codes import OP_NAMES
from search_v3a.preserve import tree_hash

RUN = ID / 'results/hierarchy_synthesis/representation-review-v1-r1'
D = ID / 'results/hierarchy_dictionary_v1/dictionary-feasibility-v1-r1'


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def component_map(data):
    ledger = archive_ledger(data)
    result = Counter()
    pos = 0
    for f in ledger['fields']:
        b = bytes.fromhex(f['hex'])
        assert len(b) == f['bytes'] and data[pos:pos + len(b)] == b
        pos += len(b)
        owner, field = f['owner'], f['field']
        if owner in ('envelope', 'dag'):
            key = owner
        elif ledger['model'] is None:
            key = ledger['codec'] + '.payload'
        else:
            op = OP_NAMES[ledger['model'].rules[int(owner[4:])].op]
            if field == 'child_id' or field.startswith('child_id['):
                part = 'refs'
            elif field in ('opcode', 'length', 'arity', 'q_flip', 'q_ap', 'q_schema', 'foreground'):
                part = 'header'
            else:
                part = 'payload'
            key = op + '.' + part
        result[key] += len(b) * 8
    assert pos == len(data) and sum(result.values()) == len(data) * 8
    return dict(result)


def main():
    before = tree_hash(RUN)
    cases = read(ID / 'protocols/hierarchy_multilevel_v1/CASES.json')['cases']
    pc = read(RUN / 'per_case.json')['rows']
    summary = read(RUN / 'summary.json')
    checks = {'case_set': len(pc) == 96 and {r['case_id'] for r in pc} == {c['case_id'] for c in cases}}
    rows = {r['case_id']: r for r in pc}
    problems = []
    margins = {'R': [], 'O': []}
    normalized = {'R': [], 'O': []}
    deltas = {'R': Counter(), 'O': Counter()}
    identity = Counter()
    raw_margins = []
    f10 = {}
    raw_paths = []
    for c in cases:
        cid = c['case_id']
        r = rows[cid]
        p = ROOT / c['references']['raw']['archive_path']
        raw_paths.append(str(p.relative_to(ID)))
        x = decode_archive(p.read_bytes())
        assert sha(p) == c['references']['raw']['archive_sha256']
        assert len(x) == c['n_bits'] and hashlib.sha256(x.encode()).hexdigest() == c['input_sha256']
        arow = read(D / 'rows' / (cid + '.A0.json'))
        a = (D / arow['archive_path']).read_bytes()
        assert hashlib.sha256(a).hexdigest() == r['a0_sha256'] == c['references']['hid_full']['archive_sha256']
        assert decode_archive(a) == x and len(a) * 8 == r['a0_bits']
        ac = component_map(a)
        if ac != r['a0_components']:
            problems.append(cid + ': A0 component labels')
        drow = read(D / 'rows' / (cid + '.D2.json'))
        tp = D / drow['trace_path']
        assert sha(tp) == drow['trace_sha256']
        props = [p for v in read(tp)['views'] for p in v['proposals'] if p['archive_bits'] is not None]
        for tag, modes in [('R', ('R(O)', 'R(P)')), ('O', ('O',))]:
            selected = min((p for p in props if p['mode'] in modes), key=lambda p: (p['archive_bits'], p['request_ordinal']))
            got = r[tag]
            h = selected['archive_sha256']
            b = (D / 'archives' / h[:2] / (h + '.isd')).read_bytes()
            assert hashlib.sha256(b).hexdigest() == got['archive_sha256'] == h
            assert selected['request_ordinal'] == got['request_ordinal']
            assert len(b) * 8 == selected['archive_bits'] == got['bits'] and decode_archive(b) == x
            comp = component_map(b)
            delta = {k: comp.get(k, 0) - ac.get(k, 0) for k in comp.keys() | ac.keys()}
            if comp != got['components'] or delta != got['component_minus_a0']:
                problems.append(cid + '.' + tag + ': component labels/deltas')
            deltas[tag].update(delta)
            margin = (len(b) - len(a)) * 8
            assert margin == got['margin_vs_a0_bits']
            assert margin / len(x) == got['margin_vs_a0_per_input_bit']
            margins[tag].append(margin)
            normalized[tag].append(margin / len(x))
            identity[tag] += b == a
            if a[4] == 0:
                raw_margins.append(margin)
            if tag == 'R' and c['family'] == 'F10' and margin == 0:
                f10[cid] = len(b) * 8
    for tag in ('R', 'O'):
        for field, values in [('margin_bits', margins[tag]), ('margin_per_input_bit', normalized[tag])]:
            vals = sorted(values)
            q = {'n': len(vals), 'min': vals[0], 'q25': vals[len(vals)//4], 'median': statistics.median(vals), 'q75': vals[3*len(vals)//4], 'max': vals[-1]}
            checks[tag + '_' + field] = q == summary[tag][field]
        checks[tag + '_component_totals'] = dict(deltas[tag]) == summary[tag]['component_minus_a0_sum_over_cases_bits']
        checks[tag + '_counts'] = [sum(v < 0 for v in margins[tag]), sum(v == 0 for v in margins[tag]), sum(v > 0 for v in margins[tag])] == summary[tag]['shorter_equal_longer_vs_a0']
        checks[tag + '_identical'] = identity[tag] == summary[tag]['byte_identical_to_a0']
    checks['all_selected_components'] = not problems
    pre = read(RUN / 'evidence_manifest_pre.json')['hashes']
    post = read(RUN / 'evidence_manifest_post.json')['hashes']
    checks['recorded_preservation'] = pre == post
    changed = []
    for name, h in post.items():
        path = (ROOT if name.startswith('index-deconvolution/') else ID) / name
        if sha(path) != h:
            changed.append(name)
    checks['current_manifest_hashes'] = not changed
    missing_raw = sorted(set(raw_paths) - set(post))
    checks['run_preserved'] = tree_hash(RUN) == before
    out = {'numeric_and_preservation_checks_pass': all(checks.values()), 'checks': checks, 'problems': problems,
           'current_manifest_drift': changed, 'raw_archive_paths_missing_from_manifest': missing_raw,
           'F10_tie_bits': f10, 'raw_A0_cases': len(raw_margins)//2, 'minimum_raw_A0_candidate_excess': min(raw_margins),
           'selections_rechecked': 192, 'run_tree': before,
           'note': 'Numeric success does not close the interpretation or delivered-audit coverage findings.'}
    (Path(__file__).parent / 'audit_review.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k not in ('raw_archive_paths_missing_from_manifest', 'run_tree')}))
    print('Missing raw archive paths:', len(missing_raw))


if __name__ == '__main__':
    main()
