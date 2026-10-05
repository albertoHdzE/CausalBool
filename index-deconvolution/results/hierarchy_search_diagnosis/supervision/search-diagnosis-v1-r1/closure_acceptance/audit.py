"""Read-only review of report-r3; writes only this review's audit.json."""
import copy
import hashlib
import json
from pathlib import Path
import runpy
import sys
import time

sys.dont_write_bytecode = True
START = time.monotonic()
HERE = Path(__file__).resolve().parent
REPO = next(p for p in HERE.parents if (p / 'index-deconvolution').is_dir())
C = REPO / 'index-deconvolution/results/hierarchy_search_diagnosis/review_closure/search-diagnosis-v1-r1-followup'
R = C / 'report-r3'
load = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
out = {}

runner = runpy.run_path(str(R / 'run_report_r3.py'), run_name='review_import')
K = runner['K']
identity = load(R / 'identity.json')
out['identity_matches'] = K.canonical_sha(runner['core']()) == identity['identity_sha256']
out['tar_matches'] = sha(R / 'closure.tar') == identity['closure_tar_sha256']
out['consumed_manifest_matches'] = runner['consumed']() == load(R / 'consumed_records.json')
old = load(HERE.parent / 'original_run_manifest.json')
root = REPO / old['root']
now = {str(p.relative_to(root)): sha(p) for p in root.rglob('*') if p.is_file()}
out['original_run'] = {'files': len(now), 'unchanged': now == old['files']}
pres = load(C / 'verification/preservation_after.json')
out['protected_named_files_differences'] = [p for field in ('files', 'extra_files')
    for p, expected in pres[field].items() if sha(REPO / p) != expected]

# Regenerate in memory only; never invoke cmd_report (which writes outputs).
b = runner['cli'].report_build(K.RUN_DIR)
out['saved_output_matches'] = {n: b[n] == load(R / 'outputs' / (('DECISION' if n == 'decision' else n) + '.json')) for n in b}
ev = b['flags']['evidence']
out['D4_counts'] = {'intended_jobs': ev['intended']['D4_jobs'],
    'job_status_counts': ev['status']['D4_jobs'],
    'conversion_status_counts': ev['status']['D4_conversions'],
    'resource_jobs': b['resources']['D4']['jobs']}

tests = runpy.run_path(str(R / 'source/search_diagnosis/tests/test_reporting_pipeline.py'))
saved = tests['saved'].__wrapped__()
cid = saved['ids']['d4'][0]
def missing(records, _saved):
    records['rec4'][(cid, 'D4')] = None
partial = tests['run'](saved, missing)
out['missing_one_D4_job'] = {'case': cid,
    'recommendation': partial['decision']['recommendation'],
    'job_status_counts': partial['flags']['evidence']['status']['D4_jobs'],
    'unavailable_jobs': partial['flags']['evidence']['unavailable']['D4_jobs'],
    'unavailable_conversions': partial['flags']['evidence']['unavailable']['D4_conversions']}

selected = next(c for c, row in b['d2_rows'].items() if row.get('B0_bytes_equal_saved_final') is True)
def mismatch(records, _saved):
    records['rec2'][(selected, 'B0')]['archives']['output']['sha256'] = '0' * 64
bad = tests['run'](saved, mismatch)
out['B0_selected_archive_hash_mismatch'] = {'case': selected,
    'byte_identity': bad['d2_rows'][selected]['B0_bytes_equal_saved_final'],
    'recommendation': bad['decision']['recommendation'],
    'valid': bad['decision']['valid'], 'gates': bad['decision']['gates']}

# Check all retained notebook executions, preserving stream order and stream name.
def normalized(nb):
    result = []
    for cell in nb['cells']:
        outputs = []
        for raw in cell.get('outputs', []):
            item = copy.deepcopy(raw)
            if item['output_type'] == 'stream':
                item['text'] = ''.join(item['text'])
                if outputs and outputs[-1]['output_type'] == 'stream' and outputs[-1]['name'] == item['name']:
                    outputs[-1]['text'] += item['text']
                    continue
            outputs.append(item)
        result.append(outputs)
    return result
notebooks = sorted((C / 'verification/notebook').glob('run*.ipynb'))
reference = normalized(load(notebooks[0]))
out['notebooks'] = {}
for p in notebooks:
    nb = load(p)
    out['notebooks'][p.name] = {
        'all_outputs_equal_after_adjacent_stream_coalescing': normalized(nb) == reference,
        'errors': sum(o['output_type'] == 'error' for c in nb['cells'] for o in c.get('outputs', [])),
        'unexecuted': sum(c['cell_type'] == 'code' and c.get('execution_count') is None for c in nb['cells'])}

prior = load(HERE.parent / 'closure_review/closure_manifest.json')
prior_root = REPO / prior['root']
prior_now = {str(p.relative_to(REPO)): sha(p) for p in prior_root.rglob('*') if p.is_file()}
out['first_closure_unchanged'] = prior_now == prior['files']
delegated = load(HERE.parent / 'closure_review/delegation_manifest.json')
out['delegation_hashes_match'] = all(sha(REPO / p) == v for p, v in delegated['files'].items())
r2 = C.parent / 'search-diagnosis-v1-r1/report-r2/outputs'
def walk(x, path=()):
    if isinstance(x, dict) and x:
        for k,v in x.items():
            yield from walk(v,path+(str(k),))
    elif isinstance(x, list) and x:
        for k,v in enumerate(x):
            yield from walk(v,path+(str(k),))
    else:
        yield '/'.join(path),x
oldflat = {}
newflat = {}
for name, obj in b.items():
    name = 'DECISION' if name == 'decision' else name
    oldflat.update(walk(load(r2 / (name+'.json')), (name,)))
    newflat.update(walk(obj, (name,)))
out['r2_differences'] = {k:[v,newflat[k]] for k,v in oldflat.items() if k in newflat and v != newflat[k]}
out['r2_removed'] = sorted(set(oldflat)-set(newflat))
out['r3_added'] = {k:newflat[k] for k in sorted(set(newflat)-set(oldflat))}
out['kernel_modules_unchanged'] = {name: sha(R/'source/search_diagnosis'/name) == sha(C.parent/'search-diagnosis-v1-r1/report-r2/source/search_diagnosis'/name) == sha(REPO/'index-deconvolution/experiments/search_diagnosis'/name) for name in ('common.py','kernels.py','runner.py','worker.py','__init__.py')}

out['elapsed_s'] = time.monotonic() - START
(HERE / 'audit.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps(out, indent=2))
