import ast, hashlib, itertools, json, pathlib, sys
R=pathlib.Path.cwd(); B=R/'index-deconvolution/results/causal_abstraction_validation'; O=B/'abstraction-validation-v1-r1'; C=B/'review_closure/abstraction-validation-v1-r1'; S=B/'supervision/abstraction-validation-v1-r1-closure'
h=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
def check(p,v):
    assert h(p)==v, str(p)
    checks.append(str(p.relative_to(R)))
f=json.loads((O/'freeze.json').read_text()); m=json.loads((O/'output_manifest.json').read_text())
for k,v in f['files'].items(): check(R/k,v)
for field in ['outputs','presentation_only']:
    for k,v in m[field].items(): check(O/k,v)
for k,v in m['permitted_repo_edits'].items(): check(R/k,v)
resolved={'core_original_sha256': O/'core_before/deconvolution.py.orig', 'packet_sha256':R/'index-deconvolution/results/causal_abstraction_design/supervision/abstraction-design-v1-r1-closure/NEXT_CLAUDE.md','review_sha256':R/'index-deconvolution/results/causal_abstraction_design/supervision/abstraction-design-v1-r1-closure/REVIEW.md','handoff_sha256':O/'HANDOFF.md'}
for k,p in resolved.items(): check(p,m[k])
check(R/'index-deconvolution/results/causal_abstraction_design/review_closure/abstraction-design-v1-r1/corrected/DRAFT_EXECUTION_PROTOCOL.md',f['draft_protocol_sha256'])
for k,v in json.loads((C/'manifest.json').read_text())['files'].items(): check(C/k,v)
sys.path.insert(0,str(R/'index-deconvolution/src'))
from deconvolution import compare_induced

def load(p):
    tree=ast.parse(p.read_text()); node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='evaluate_classes'); ns={'PASS':'PASS','FAIL':'FAIL','compare_induced':compare_induced}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(p),'exec'),ns)
    return ns['evaluate_classes']
a=load(O/'study.py'); b=load(C/'corrected_source/study.py.txt'); n=0; labels=set()
for cls in [[[0]],[[0,1]],[[0,1,2]],[[0],[1,2]],[[0],[1],[2]]]:
    ids=set(sum(cls,[]))
    for vals in itertools.product([None,{0:0,1:1},{0:1,1:0}],repeat=len(ids)):
        maps=dict(zip(sorted(ids),vals)); old=a(cls,maps,ids,{0:1,1:1},2); new=b(cls,maps,ids,{0:1,1:1},2)
        assert {k:new[k] for k in old}==old
        assert new['availability']=={'missing_records':0,'missing_comparisons':0}
        labels.add(old['label']); n+=1
assert len(labels)==4
out={'verified_hash_entries':len(checks),'five_metadata_hashes_resolved':True,'complete_inputs_exhaustively_compared_small_domain':n,'labels':sorted(labels),'files':checks}
(S/'review_check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='files'}))
