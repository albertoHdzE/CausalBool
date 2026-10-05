"""Numbers quoted in the original SYNTHESIS.md/HANDOFF.md prose, recomputed from saved
bytes through closure_audit.observe(), plus the files-read-within-manifest check.
The corrected prose quotes only these numbers (or numbers in the checked tables)."""
import json
import statistics
from collections import Counter

from closure_audit import HERE, observe, READS


def main():
    obs = observe()[0]
    rows = list(obs.values())
    raw = [r for r in rows if r['a0_codec'] == 'raw']
    hid = [r for r in rows if r['a0_codec'] != 'raw']
    R, O = (lambda rs, t: [r[t]['margin_vs_a0_bits'] for r in rs]), None
    tot = Counter()
    for r in rows:
        tot.update(r['R']['component_minus_a0'])
    fam = lambda k: sum(v for c, v in tot.items() if c.startswith(k + '.'))  # noqa: E731
    eq = {r_id: r['R']['bits'] for r_id, r in obs.items() if r['R']['margin_vs_a0_bits'] == 0}
    claims = {
        'raw_A0_strings': (len(raw), 30),
        'raw_A0_families': (sorted({r['family'] for r in raw}), ['F02', 'F07', 'F08', 'F09', 'F11']),
        'raw_A0_best_margin_range': ([min(R(raw, 'R') + R(raw, 'O')), max(R(raw, 'R') + R(raw, 'O'))], [408, 1608]),
        'raw_A0_median_R_O': ([statistics.median(R(raw, 'R')), statistics.median(R(raw, 'O'))], [484, 456]),
        'hid_A0_range': ([min(R(hid, 'R') + R(hid, 'O')), max(R(hid, 'R') + R(hid, 'O'))], [0, 4384]),
        'hid_A0_median_R_O': ([statistics.median(R(hid, 'R')), statistics.median(R(hid, 'O'))], [652, 528]),
        'R_equal_cases_bits': (sorted(eq.items()), sorted({
            'confirmation-F05-1024-3000-base': 144, 'confirmation-F05-1024-3000-ragged': 200,
            'confirmation-F10-1024-3000-base': 440, 'confirmation-F10-1024-3001-base': 440,
            'confirmation-F10-4096-3000-base': 696, 'confirmation-F10-4096-3001-base': 688}.items())),
        'R_component_family_sums': ({k: fam(k) for k in ('XFORM', 'PATCH', 'REPEAT', 'AP_UNION', 'SCHEMA_UNION')},
                                    {'XFORM': 9728, 'PATCH': 10528, 'REPEAT': 1992, 'AP_UNION': -2624, 'SCHEMA_UNION': -416}),
    }
    out = {k: {'recomputed': a, 'quoted': b, 'equal': a == b} for k, (a, b) in claims.items()}
    man = json.loads((HERE / 'closure_manifest_pre.json').read_text())['hashes']
    out['files_read_within_closure_manifest'] = {'read': len(READS), 'outside_manifest': sorted(READS - set(man))}
    out['all_equal'] = all(v['equal'] for k, v in out.items() if 'equal' in v) and not out['files_read_within_closure_manifest']['outside_manifest']
    (HERE / 'numeric_equality.json').write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
