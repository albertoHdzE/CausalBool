"""Read-only review of the frozen run; outputs only into this supervision folder."""
import builtins
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path.cwd()
RUN = ROOT / 'index-deconvolution/results/causal_abstraction_validation/abstraction-validation-v1-r1'
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'index-deconvolution/src'))
def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
before = {str(p): digest(p) for p in RUN.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
spec = importlib.util.spec_from_file_location('review_oracle', RUN/'audit_oracle.py')
o = importlib.util.module_from_spec(spec)
spec.loader.exec_module(o)
real_open = builtins.open
def guarded_open(file, mode='r', *args, **kwargs):
    if any(c in mode for c in 'wax+'):
        if Path(file).resolve() != RUN/'audit.json':
            raise RuntimeError(f'Unexpected write: {file}')
        file = OUT/'oracle_rerun.json'
    return real_open(file, mode, *args, **kwargs)
builtins.open = guarded_open
try:
    try:
        o.main()
    except SystemExit as e:
        assert e.code == 0
finally:
    builtins.open = real_open
rows = [json.loads(l) for l in (RUN/'results_d.jsonl').read_text().splitlines()]
fx = json.loads((RUN/'fixtures.json').read_text())
assert all(r['candidate'] == {k:v for k,v in fx['candidates'][str(10 if r['model']=='M4' else 8)][r['cand_id']].items() if k!='id'} for r in rows)
assert all(r['beta_fine_all_singletons'] for r in rows)
# Independently recompute every FULL non-projection partition and every induced map.
render = {r['row']:r for r in json.loads((RUN/'nonf3_full_maps.json').read_text())}
tables = {m:o.one_step(m) for m in ['M3','M4']}
render_checked = []
for r in rows:
    if r['display'] != 'FULL' or r['candidate']['family']=='F3':
        continue
    n = 10 if r['model']=='M4' else 8
    c = o.family(n)[r['cand_id']]
    lab = o.labels([o.macro(c,x,n) for x in range(2**n)])
    published = render[r['row']]
    maps = {}
    for entry in published['distinct_maps']:
        for name in entry['q']:
            maps[name] = {int(k):v for k,v in entry['G'].items()}
    for q in o.interventions(n):
        op,j,c0 = q
        name = op if op in ('id','tick') else (f'flip{j}' if op=='flip' else f'{op}{j}_{c0}')
        image = [lab[y] for y in o.intervened(tables[r['model']],n,q,r['tau'])]
        expected, w = o.exists_and_witness(lab,image)
        assert w is None and expected == maps[name], (r['row'],name)
    render_checked.append(r['row'])
pre=json.loads((RUN/'preservation_before.json').read_text())['files']
post=json.loads((RUN/'preservation_after.json').read_text())['files']
changes=[k for k in pre if post.get(k)!=pre[k]]
added=sorted(set(post)-set(pre))
assert changes==['index-deconvolution/src/deconvolution.py']
assert added==['index-deconvolution/tests/test_abstraction.py']
assert all(digest(Path(k))==v for k,v in post.items())
assert before == {str(p):digest(p) for p in RUN.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
result={'pass':True,'oracle_checks':18,'candidate_metadata_checked':len(rows),'nonprojection_full_maps_independently_checked':render_checked,'preserved_files_currently_rehashed':len(post),'run_files_unchanged':len(before),'changes':changes,'added':added,'display_counts':dict(collections.Counter(r['display'] for r in rows))}
(OUT/'audit_review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
