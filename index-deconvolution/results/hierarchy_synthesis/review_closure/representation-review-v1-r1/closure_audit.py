"""Closure audit (review R2) for representation-review-v1-r1.

Imports neither the synthesis analysis.py/audit.py nor the supervisor's
audit_review.py. Owners shared by intention: hierarchy.decode.decode_archive,
hierarchy.ledger.archive_ledger, hierarchy.codes.OP_NAMES.

observe() rebuilds every reported quantity from saved bytes (raw archives, A0
archives, D2 traces, selected archives). verify() compares it with the reported
tables field by field. The exact 96-case set is enforced before any other
comparison. Three in-memory corruptions of the reported tables must each be
rejected by the intended check; the real tables must pass. Writes only here.
"""
import copy
import csv
import hashlib
import io
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
ID = ROOT / 'index-deconvolution'
sys.path[:0] = [str(ID)]
from hierarchy.decode import decode_archive  # noqa: E402
from hierarchy.ledger import archive_ledger  # noqa: E402
from hierarchy.codes import OP_NAMES  # noqa: E402

RUN = ID / 'results/hierarchy_synthesis/representation-review-v1-r1'
D = ID / 'results/hierarchy_dictionary_v1/dictionary-feasibility-v1-r1'
CASES = ID / 'protocols/hierarchy_multilevel_v1/CASES.json'
READS = set()
HEADER = ('opcode', 'length', 'arity', 'q_flip', 'q_ap', 'q_schema', 'foreground')


def rb(p):
    READS.add(str(p.resolve().relative_to(ROOT)))
    return p.read_bytes()


def rj(p):
    return json.loads(rb(p))


def h(b):
    return hashlib.sha256(b).hexdigest()


def quantiles(vals):
    """The synthesis's declared definition (analysis.py `q`), restated, not imported."""
    v = sorted(vals)
    return {'n': len(v), 'min': v[0], 'q25': v[len(v) // 4], 'median': statistics.median(v),
            'q75': v[3 * len(v) // 4], 'max': v[-1]}


def components(data):
    """Independent field-to-component labelling of the owner ledger."""
    led = archive_ledger(data)
    out, pos = Counter(), 0
    for f in led['fields']:
        b = bytes.fromhex(f['hex'])
        if len(b) != f['bytes'] or data[pos:pos + len(b)] != b:
            raise ValueError('ledger field does not tile the archive')
        pos += len(b)
        owner, field = f['owner'], f['field']
        if owner in ('envelope', 'dag'):
            key = owner
        elif led['model'] is None:
            key = led['codec'] + '.payload'
        else:
            op = OP_NAMES[led['model'].rules[int(owner[4:])].op]
            part = ('refs' if field == 'child_id' or field.startswith('child_id[')
                    else 'header' if field in HEADER else 'payload')
            key = op + '.' + part
        out[key] += len(b) * 8
    if pos != len(data):
        raise ValueError('ledger does not cover the archive')
    kinds = None if led['model'] is None else sorted({OP_NAMES[r.op] for r in led['model'].rules})
    return dict(out), led['codec'], kinds


def observe():
    cases = rj(CASES)['cases']
    obs, integrity = {}, Counter()
    for c in cases:
        cid = c['case_id']
        raw = c['references']['raw']
        rawb = rb(ROOT / raw['archive_path'])
        x = decode_archive(rawb)
        integrity['raw_hash_vs_CASES_pin'] += h(rawb) == raw['archive_sha256']
        integrity['input_n_vs_CASES'] += len(x) == c['n_bits']
        integrity['input_sha_vs_CASES'] += hashlib.sha256(x.encode()).hexdigest() == c['input_sha256']
        arow = rj(D / 'rows' / f'{cid}.A0.json')
        a = rb(D / arow['archive_path'])
        integrity['A0_hash_vs_k1_pin'] += h(a) == arow['archive_sha256'] == c['references']['hid_full']['archive_sha256']
        integrity['A0_decodes'] += decode_archive(a) == x
        ac, codec, kinds = components(a)
        rec = {'family': c['family'], 'n_bits': len(x), 'a0_sha256': h(a), 'a0_bits': len(a) * 8,
               'a0_components': ac, 'a0_codec': codec, 'a0_kinds': kinds}
        drow = rj(D / 'rows' / f'{cid}.D2.json')
        tp = D / drow['trace_path']
        trace = rj(tp)
        integrity['trace_hash_vs_row'] += h(rb(tp)) == drow['trace_sha256']
        props = [dict(p, view=[v['level'], v['width'], v['origin']])
                 for v in trace['views'] for p in v['proposals'] if p['archive_bits'] is not None]
        for tag, modes in (('R', ('R(O)', 'R(P)')), ('O', ('O',))):
            s = min((p for p in props if p['mode'] in modes), key=lambda p: (p['archive_bits'], p['request_ordinal']))
            b = rb(D / 'archives' / s['archive_sha256'][:2] / (s['archive_sha256'] + '.isd'))
            integrity['selected_hash'] += h(b) == s['archive_sha256']
            integrity['selected_bits'] += len(b) * 8 == s['archive_bits']
            integrity['selected_decodes'] += decode_archive(b) == x
            comp = components(b)[0]
            m = len(b) * 8 - len(a) * 8
            rec[tag] = {'mode': s['mode'], 'proposal': s['proposal'], 'request_ordinal': s['request_ordinal'],
                        'view': s['view'], 'archive_sha256': h(b), 'bits': len(b) * 8,
                        'margin_vs_a0_bits': m, 'margin_vs_a0_per_input_bit': m / len(x),
                        'byte_identical_to_a0': b == a, 'components': comp,
                        'component_minus_a0': {k: comp.get(k, 0) - ac.get(k, 0) for k in comp.keys() | ac.keys()}}
        rec['R_minus_O_bits'] = rec['R']['bits'] - rec['O']['bits']
        obs[cid] = rec
    return obs, dict(integrity), len(cases)


def expected_summary(obs):
    """Everything the summary reports that is derivable from saved bytes."""
    out = {}
    rows = list(obs.values())
    for tag in ('R', 'O'):
        sel = [r[tag] for r in rows]
        tot, pos = Counter(), Counter()
        for s in sel:
            tot.update(s['component_minus_a0'])
            pos.update(k for k, v in s['component_minus_a0'].items() if v > 0)
        ms = [s['margin_vs_a0_bits'] for s in sel]
        out[tag] = {'available': len(sel), 'unavailable': 0,
                    'byte_identical_to_a0': sum(s['byte_identical_to_a0'] for s in sel),
                    'margin_bits': quantiles(ms),
                    'margin_per_input_bit': quantiles([s['margin_vs_a0_per_input_bit'] for s in sel]),
                    'shorter_equal_longer_vs_a0': [sum(m < 0 for m in ms), sum(m == 0 for m in ms), sum(m > 0 for m in ms)],
                    'component_minus_a0_sum_over_cases_bits': dict(tot),
                    'component_minus_a0_cases_positive': dict(pos),
                    'modes': dict(Counter(s['mode'] for s in sel)),
                    'proposals': dict(Counter(s['proposal'] for s in sel)),
                    'views_width_level': dict(Counter(f"w{s['view'][1]}-l{s['view'][0]}" for s in sel))}
    d = [r['R_minus_O_bits'] for r in rows]
    out['best_R_minus_best_O'] = {'dist': quantiles(d), 'n': len(d), 'shorter': sum(v < 0 for v in d),
                                  'equal': sum(v == 0 for v in d), 'longer': sum(v > 0 for v in d)}
    out['a0_codecs'] = dict(Counter(r['a0_codec'] for r in rows))
    out['a0_rule_kinds_present'] = dict(Counter(k for r in rows for k in (r['a0_kinds'] or [])))
    out['beats_A0_strings_R_O'] = [sum(r[t]['margin_vs_a0_bits'] < 0 for r in rows) for t in ('R', 'O')]
    return out


ROW_FIELDS = ('family', 'n_bits', 'a0_sha256', 'a0_bits', 'a0_components', 'R_minus_O_bits')
SEL_FIELDS = ('mode', 'proposal', 'request_ordinal', 'view', 'archive_sha256', 'bits', 'margin_vs_a0_bits',
              'margin_vs_a0_per_input_bit', 'byte_identical_to_a0', 'components', 'component_minus_a0')


def verify(obs, pc_rows, summary, pc_csv, comp_csv):
    checks, why = {}, {}
    ids = [r['case_id'] for r in pc_rows]
    dup = sorted(k for k, n in Counter(ids).items() if n > 1)
    checks['exact_case_set'] = len(ids) == 96 and not dup and set(ids) == set(obs)
    why['exact_case_set'] = {'n_rows': len(ids), 'duplicates': dup,
                             'missing': sorted(set(obs) - set(ids)), 'extra': sorted(set(ids) - set(obs))}
    if not checks['exact_case_set']:
        return checks, why, 'stopped: case set not exact; no further comparison computed'
    rows = {r['case_id']: r for r in pc_rows}
    bad_fields, sum_only = [], []
    for cid, o in obs.items():
        r = rows[cid]
        bad_fields += [f'{cid}.{f}' for f in ROW_FIELDS if r.get(f) != o[f]]
        if r['a0_info']['codec'] != o['a0_codec']:
            bad_fields.append(f'{cid}.a0_info.codec')
        for tag in ('R', 'O'):
            bad_fields += [f'{cid}.{tag}.{f}' for f in SEL_FIELDS if r[tag].get(f) != o[tag][f]]
            if sum(r[tag]['components'].values()) != r[tag]['bits']:
                sum_only.append(f'{cid}.{tag}')
    checks['per_case_fields'] = not bad_fields
    why['per_case_fields'] = bad_fields[:20]
    checks['component_sums_equal_bits'] = not sum_only
    why['component_sums_equal_bits'] = sum_only[:20]
    exp = expected_summary(obs)
    bad_summary = []
    for tag in ('R', 'O'):
        for k, v in exp[tag].items():
            got = summary[tag].get(k) if k != 'unavailable' else summary[tag].get('unavailable')
            if got != v:
                bad_summary.append(f'{tag}.{k}')
            if isinstance(v, dict) and k.startswith('margin'):
                bad_summary += [f'{tag}.{k}.{q}' for q in v if summary[tag][k].get(q) != v[q]]
    for k in ('best_R_minus_best_O', 'a0_codecs', 'a0_rule_kinds_present'):
        if summary[k] != exp[k]:
            bad_summary.append(k)
    if summary['three_notions']['beats_A0_strings_R_O'] != exp['beats_A0_strings_R_O']:
        bad_summary.append('three_notions.beats_A0_strings_R_O')
    if summary['three_notions']['best_over_views_R_vs_O_strings'] != [exp['best_R_minus_best_O'][k] for k in ('shorter', 'equal', 'longer')]:
        bad_summary.append('three_notions.best_over_views_R_vs_O_strings')
    checks['summary_all_derivable_fields'] = not bad_summary
    why['summary_all_derivable_fields'] = bad_summary
    bad_csv = []
    for line in pc_csv:
        o = obs.get(line['case_id'])
        if o is None or [line['a0_bits'], line['R_bits'], line['O_bits'], line['R_margin_bits'], line['O_margin_bits'],
                         line['R_minus_O_bits'], line['R_sha256'], line['O_sha256'], line['a0_sha256'], line['R_mode']] != \
                [str(o['a0_bits']), str(o['R']['bits']), str(o['O']['bits']), str(o['R']['margin_vs_a0_bits']),
                 str(o['O']['margin_vs_a0_bits']), str(o['R_minus_O_bits']), o['R']['archive_sha256'],
                 o['O']['archive_sha256'], o['a0_sha256'], o['R']['mode']]:
            bad_csv.append(line['case_id'])
    checks['per_case_csv'] = not bad_csv and len(pc_csv) == 96
    why['per_case_csv'] = bad_csv[:20]
    want = Counter((cid, arch, k, str(v)) for cid, o in obs.items()
                   for arch, comp in (('A0', o['a0_components']), ('best_R', o['R']['components']), ('best_O', o['O']['components']))
                   for k, v in comp.items())
    got = Counter((l['case_id'], l['archive'], l['component'], l['bits']) for l in comp_csv)
    checks['per_case_components_csv'] = want == got
    why['per_case_components_csv'] = {'only_reported': len(got - want), 'only_reconstructed': len(want - got),
                                      'archive_labels_seen': sorted({k[1] for k in got})}
    return checks, why, 'complete'


def corruptions(pc_rows, summary):
    """Three meaningful corruptions of the reported tables (in memory only)."""
    out = {}
    rows = copy.deepcopy(pc_rows)
    tgt = next(r for r in rows if r['R']['components'].get('CONCAT.refs', 0) >= 8 and 'LITERAL.payload' in r['R']['components'])
    for k, d in (('CONCAT.refs', -8), ('LITERAL.payload', 8)):
        tgt['R']['components'][k] += d
        tgt['R']['component_minus_a0'][k] += d
    out['transfer_8_bits_CONCAT.refs_to_LITERAL.payload'] = (rows, summary, 'per_case_fields', tgt['case_id'] + '.R')
    s = copy.deepcopy(summary)
    s['R']['margin_bits']['q25'] += 8
    out['R_margin_bits_q25_plus_8'] = (pc_rows, s, 'summary_all_derivable_fields', 'R.margin_bits.q25')
    rows = copy.deepcopy(pc_rows)
    rows[-1] = copy.deepcopy(rows[0])
    out['last_case_replaced_by_duplicate_of_first'] = (rows, summary, 'exact_case_set', pc_rows[-1]['case_id'])
    return out


def main():
    obs, integrity, n_cases = observe()
    pc_rows = rj(RUN / 'per_case.json')['rows']
    summary = rj(RUN / 'summary.json')
    pc_csv = list(csv.DictReader(io.StringIO(rb(RUN / 'per_case.csv').decode())))
    comp_csv = list(csv.DictReader(io.StringIO(rb(RUN / 'per_case_components.csv').decode())))
    checks, why, status = verify(obs, pc_rows, summary, pc_csv, comp_csv)
    integrity_ok = n_cases == 96 and all(v == 96 for k, v in integrity.items() if not k.startswith('selected')) \
        and all(v == 192 for k, v in integrity.items() if k.startswith('selected'))
    corr = {}
    for name, (rows, summ, intended, locus) in corruptions(pc_rows, summary).items():
        c, w, st = verify(obs, rows, summ, pc_csv, comp_csv)
        failed = sorted(k for k, v in c.items() if not v)
        corr[name] = {'intended_check': intended, 'locus': locus, 'failed_checks': failed, 'status': st,
                      'intended_failed': intended in failed, 'intended_reason': w.get(intended),
                      'component_sums_equal_bits_still_pass': c.get('component_sums_equal_bits'),
                      'rejected_for_intended_reason': intended in failed and (
                          locus in json.dumps(w.get(intended)) or intended == 'exact_case_set')}
    out = {'real_data_pass': integrity_ok and status == 'complete' and all(checks.values()),
           'n_cases': n_cases, 'input_integrity_counts': integrity, 'checks': checks, 'details': why,
           'status': status, 'corruptions': corr,
           'all_corruptions_rejected_for_intended_reason': all(v['rejected_for_intended_reason'] for v in corr.values()),
           'not_rechecked': ['three_notions.within_view_* (copied from the accepted dictionary summary; outside R2)'],
           'files_read': sorted(READS)}
    (HERE / 'closure_audit_result.json').write_text(json.dumps(out, indent=1, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k not in ('files_read', 'details')}, indent=1))
    print('files read:', len(READS))
    sys.exit(0 if out['real_data_pass'] and out['all_corruptions_rejected_for_intended_reason'] else 1)


if __name__ == '__main__':
    main()
