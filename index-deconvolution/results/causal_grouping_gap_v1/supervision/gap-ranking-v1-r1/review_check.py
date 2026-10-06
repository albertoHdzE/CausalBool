"""Supplemental Codex checks; read artifacts only, import no study producers."""
import hashlib
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
RUN = ROOT / 'index-deconvolution/results/causal_grouping_gap_v1/gap-ranking-v1-r1'
HERE = Path(__file__).resolve().parent


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


checks = {}
freeze = read(RUN / 'freeze.json')
for name, base, entries in (
    ('frozen_files', RUN, freeze['files']),
    ('expected_inputs', ROOT, freeze['expected_inputs']),
    ('output_manifest', RUN, read(RUN / 'output_manifest.json')['sha256']),
):
    for path, digest in entries.items():
        assert sha(base / path) == digest, (name, path)
    checks[name] = len(entries)

prod = RUN / 'production'
ranks = read(prod / 'ranks.json')
joined = read(prod / 'joined.json')
cells = joined['cells']
expected = {(m, t) for m in ('M1', 'M2', 'M3', 'M4') for t in (1, 2, 4, 8, 16)}
assert len(cells) == len(ranks) == 20
assert {(c['model'], c['tau']) for c in cells} == expected
assert {(c['model'], c['tau']) for c in ranks} == expected
rank_by = {(c['model'], c['tau']): c for c in ranks}
labels = {}
old = ROOT / 'index-deconvolution/results/causal_abstraction_validation/abstraction-validation-v1-r1'
for line in (old / 'results_d.jsonl').read_text().splitlines():
    row = json.loads(line)
    key = row['model'], row['cand_id'], row['tau']
    assert key not in labels
    labels[key] = row
assert len(labels) == 2730
counts = {k: Counter() for k in ('vs_random', 'vs_canonical')}
missing, constant = [], []
for cell in cells:
    mid, tau = cell['model'], cell['tau']
    r = rank_by[mid, tau]
    for field in ('gap_order', 'canonical_order'):
        assert cell[field] == r[field]
        assert len(cell[field]) == len(set(cell[field])) == cell['N']
    full = [i for i in r['canonical_order'] if labels[mid, i, tau]['status'] == 'FULL']
    assert cell['full_ids'] == full and cell['m'] == len(full)
    if not full:
        assert cell['status'] == 'NO_FULL_REFERENCE'
        for field in ('r_G', 'r_C', 'random_expected', 'delta_random', 'delta_canonical',
                      'vs_random', 'vs_canonical', 'first_hit'):
            assert cell[field] is None, (mid, tau, field)
        missing.append([mid, tau])
        continue
    rg = next(i for i, cid in enumerate(r['gap_order'], 1) if cid in full)
    rc = next(i for i, cid in enumerate(r['canonical_order'], 1) if cid in full)
    assert (cell['r_G'], cell['r_C']) == (rg, rc)
    ex = Fraction(cell['N'] + 1, len(full) + 1)
    assert cell['random_expected']['reduced'] == [ex.numerator, ex.denominator]
    for field, delta in (('vs_random', ex-rg), ('vs_canonical', Fraction(rc-rg))):
        label = 'EARLIER' if delta > 0 else 'LATER' if delta < 0 else 'TIE'
        assert cell[field] == label
        counts[field][label] += 1
    assert cell['canonical_first_hit'] == r['canonical_order'][rc-1]
    hit = cell['first_hit']
    assert hit['candidate'] == labels[mid, hit['id'], tau]['candidate']
    if hit['dynamics'] == 'CONSTANT_DYNAMICS':
        constant.append([mid, tau, hit['id']])
for field, tally in counts.items():
    assert joined['summary'][field] == {k: tally[k] for k in ('EARLIER', 'TIE', 'LATER')}
assert joined['summary']['unavailable_cells'] == missing
assert joined['summary']['constant_dynamics_first_hits'] == constant
checks.update(endpoint_cells=20, null_cells=len(missing), known_constant_first_hits=len(constant))

occ = Counter()
for line in (prod / 'occurrences.jsonl').read_text().splitlines():
    row = json.loads(line)
    occ[row['model'], row['tau'], row['w'], row['o']] += 1
for s in read(prod / 'scores.json'):
    assert s['n_sets'] == occ[s['model'], s['tau'], s['w'], s['o']]
    assert s['frames'] == 64 // s['tau'] + 1
checks['score_metadata'] = 180

repro = Path('/tmp/gap_codex_review_20261005_repro')
equal = []
for p in sorted(prod.iterdir()):
    if p.name != 'cost.json':
        assert p.read_bytes() == (repro / 'production' / p.name).read_bytes(), p.name
        equal.append(p.name)
assert (RUN / 'audit/audit.json').read_bytes() == (repro / 'audit/audit.json').read_bytes()
checks['reproduced_production_files'] = equal
checks['timing_file_excluded_from_byte_equality'] = 'cost.json'
assert read(repro / 'audit/audit.json')['status'] == 'VALID_COMPLETE'
checks['audit_rerun'] = read(repro / 'audit/audit.json')
checks['corruptions_rerun'] = read(repro / 'audit/corruptions.json')
(HERE / 'review_check.json').write_text(json.dumps(checks, indent=2) + '\n')
print(json.dumps({k: v for k, v in checks.items() if k not in ('audit_rerun', 'corruptions_rerun')}))
