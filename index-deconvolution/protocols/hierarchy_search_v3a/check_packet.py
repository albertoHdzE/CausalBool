"""Read-only pre-edit packet checks. No corpus generation or inference.

Run from repository root: venv/bin/python -B <this file>.
After implementation the initial source equality is expected to differ; this is
not the scientific freeze validator and must not be used to waive that validator.
"""
import ast
import hashlib
import json
from pathlib import Path

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[2]
ROOT = REPO / 'index-deconvolution'


def main():
    contract = json.loads((PACKET / 'contract.json').read_text())
    state = json.loads((PACKET / 'INITIAL_SOURCE_STATE.json').read_text())
    cases = json.loads((PACKET / 'intended_cases.json').read_text())['cases']
    checks = {}

    def check(name, condition):
        checks[name] = bool(condition)

    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    check('case_ids_unique', len({r['case_id'] for r in cases}) == 256)
    check('primary_120_pairs_240_strings', sum(r['primary'] for r in cases) == 240
          and sum(r['primary'] and not r['ragged'] for r in cases) == 120)
    check('control_8_pairs_16_strings', sum(not r['primary'] for r in cases) == 16)
    cells = {}
    for r in cases:
        if r['primary']:
            cells.setdefault((r['role'], r['family'], r['base_length']), set()).add(r['replicate'])
    check('six_cells_twenty_units_each', len(cells) == 6 and all(len(v) == 20 for v in cells.values()))
    check('encoded_and_derived_counts', len(cases) * (2 + len(contract['baselines'])) == 2816
          and len(cases) * 12 == 3072)
    budgets = contract['resources']
    check('eight_hour_partition', sum(budgets['category_caps_s'].values()) == budgets['total_s'] == 28800)
    check('report_reserve', budgets['report_finalization_reserve_s'] + budgets['supervisor_review_reserve_s'] == 600)
    dev = contract['development']
    check('development_counts', len(dev['control_case_ids']) == 1792
          and len(dev['target_case_ids']) == 176 and len(dev['control_case_ids_for_paired_comparison']) == 32
          and dev['distinct_worker_jobs'] == 2000)
    check('development_groups_disjoint', not set(dev['target_case_ids']) & set(dev['control_case_ids_for_paired_comparison']))
    check('prospective_ids_distinct', not {r['case_id'] for r in cases} & set(dev['control_case_ids']))
    check('paired_lengths', all(r['n_bits'] == r['base_length'] + 3 * r['ragged'] for r in cases))
    check('new_run_not_started', not (ROOT / 'results/hierarchy_search_v3a').exists())
    check('notebook20_unoccupied', all(not (REPO / contract['notebook'][k]).exists() for k in ('builder', 'notebook')))
    patch = contract['median_patch']
    check('median_patch_hash', sha(REPO / patch['path']) == patch['sha256'])
    for category in ('source_hashes', 'protected_file_hashes'):
        check(category + '_unchanged', all((REPO / k).is_file() and sha(REPO / k) == v for k, v in state[category].items()))
    syntax = ast.parse((ROOT / 'hierarchy/segmentation.py').read_text())
    cls = next(x for x in syntax.body if isinstance(x, ast.ClassDef) and x.name == 'BoundaryConfig')
    defaults = {x.target.id: ast.literal_eval(x.value) for x in cls.body if isinstance(x, ast.AnnAssign)}
    check('boundary_defaults_match_owner', defaults == contract['boundary_config'])
    syntax = ast.parse((ROOT / 'hierarchy/baselines.py').read_text())
    baselines = next(ast.literal_eval(x.value) for x in syntax.body if isinstance(x, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'BASELINE_METHODS' for t in x.targets))
    check('baseline_order_matches_owner', list(baselines) == contract['baselines'])
    check('trace_bound', 8192 > 7 * (7 * 33 + 4 * 5 * 19))
    check('no_efficacy_selection', dev['efficacy_gate'] is None and not contract['analysis']['other_intervals'])
    plan = contract['analysis']
    check('single_fixed_bootstrap', plan['primary_contrasts'] == 1 and plan['bootstrap_seed'] == 55001
          and plan['bootstrap_draws'] == 10000 and plan['interval_level'] == .99)
    manifest_path = PACKET / 'DELEGATION_MANIFEST.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        check('delegation_hashes', all((REPO / k).is_file() and sha(REPO / k) == v
                                      for k, v in manifest['files'].items()))
    print(json.dumps({'all_pass': all(checks.values()), 'checks': checks,
                      'primary_cells': [{'role': k[0], 'family': k[1], 'base_length': k[2], 'units': len(v)}
                                        for k, v in sorted(cells.items())],
                      'scope': 'static pre-edit checks; no generated data or algorithm execution'}, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
