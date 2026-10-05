import hashlib,json,pathlib,subprocess
R=pathlib.Path.cwd();B=R/'index-deconvolution/results/causal_abstraction_validation';O=B/'abstraction-validation-v1-r1';C=B/'review_closure/abstraction-validation-v1-r1';S=B/'supervision/abstraction-validation-v1-r1-closure'; V=B/'abstraction-validation-v1-r1-source-r2'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected={str(p.relative_to(R)):h(p) for root in [O,C] for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
originals={}
for rel in ['index-deconvolution/src/deconvolution.py','index-deconvolution/tests/test_abstraction.py']:
 p=R/rel; data=p.read_bytes();target=S/(p.name+'.frozen.txt');target.write_bytes(data);originals[rel]={'sha256':h(p),'snapshot':str(target.relative_to(R))}
V.mkdir()
for name in ['study.py','test_study.py']:(V/name).write_bytes((C/'corrected_source'/(name+'.txt')).read_bytes())
(V/'fixtures.json').write_bytes((O/'fixtures.json').read_bytes())
patches=[C/'patches/R2_deconvolution.patch',C/'patches/R2_test_abstraction.patch']
subprocess.run(['git','apply','--check',*map(str,patches)],check=True)
subprocess.run(['git','apply',*map(str,patches)],check=True)
for name,rel in [('deconvolution.py','index-deconvolution/src/deconvolution.py'),('test_abstraction.py','index-deconvolution/tests/test_abstraction.py')]:assert (R/rel).read_bytes()==(C/'corrected_source'/(name+'.txt')).read_bytes()
for rel,digest in protected.items():assert h(R/rel)==digest,rel
out={'revision':'causal-state-grouping-source-r2','originals':originals,'adopted':{str(p.relative_to(R)):h(p) for p in [R/'index-deconvolution/src/deconvolution.py',R/'index-deconvolution/tests/test_abstraction.py',V/'study.py',V/'test_study.py',V/'fixtures.json']},'protected_files_unchanged':len(protected),'historical_freeze_not_amended':True,'new_scientific_execution_authorized':False}
(S/'adoption.json').write_text(json.dumps(out,indent=2)+'\n')
(V/'README.md').write_text('''# Causal state grouping — source revision r2

Accepted robustness correction to abstraction-validation-v1-r1. This is a separately identified source revision, not a new study or a replacement result. study.py and test_study.py are byte-identical to the reviewed Claude correction. The original frozen study and all V/D/X results remain unchanged. No production runner or execution authorization is supplied.

R1 corrects incomplete-evidence decisions; R2 is adopted in the existing core owner. Identity and preserved frozen core/test bytes are in ../supervision/abstraction-validation-v1-r1-closure/adoption.json. The original freeze still describes the historical sources; the active core now has a new identity. To reproduce the historical freeze, use an isolated repository copy and restore the two snapshots listed there to their original paths. Do not rewrite the old freeze or its source in place.

Run regression tests from the repository root with PYTHONDONTWRITEBYTECODE=1 and PYTHONPATH=index-deconvolution/src using pytest -p no:cacheprovider, the active tests/test_deconvolution.py and tests/test_abstraction.py, and this revision's test_study.py. This runs fixture tests only.
''')
print(json.dumps(out,indent=2))
