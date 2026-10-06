import json, pathlib, shutil, subprocess, os
root=pathlib.Path('/Users/alberto/Documents/projects/CausalBool')
b=root/'index-deconvolution/results/causal_task_compaction_v1'
c=b/'review_closure/task-compaction-v1-r1'
d=pathlib.Path('/tmp/task_compaction_r2_extra_probes');d.mkdir(exist_ok=False)
results=[]
for name in ['candidate_bool','candidate_metadata','summary_both_bool']:
 p=d/name;shutil.copytree(b/'task-compaction-v1-r1/production',p)
 if name.startswith('candidate'):
  f=p/'candidates/cell_00.jsonl'; rows=[json.loads(x) for x in f.read_text().splitlines()]
  if name=='candidate_bool': rows[0]['decodable']=1;rows[0]['K_candidate']=256.0
  else: rows[0]['cell_id']=999;rows[0]['candidate']['g']='invented'
  f.write_text(''.join(json.dumps(x)+'\n' for x in rows))
 else:
  f=p/'cells/cell_00.json';a=json.loads(f.read_text());a['summary']['baselines']['identity']['task_sufficient']=1;f.write_text(json.dumps(a))
  f=p/'summary.json';a=json.loads(f.read_text());a['cells'][0]['baselines']['identity']['task_sufficient']=1;f.write_text(json.dumps(a))
 out=d/(name+'_audit')
 r=subprocess.run([str(root/'venv/bin/python'),str(c/'src/audit_r2.py'),str(p),str(out),'--bypass-integrity'],env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True)
 (d/(name+'.log')).write_text(r.stdout+r.stderr)
 a=json.loads((out/'audit.json').read_text()) if (out/'audit.json').exists() else {}
 results.append(dict(probe=name,returncode=r.returncode,status=a.get('status'),invalid=a.get('invalid'),missing=a.get('missing')))
(d/'results.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
