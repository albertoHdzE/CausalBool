from pathlib import Path
import itertools,json,time,hashlib
import machine
import direct_compiler as dc
from research import structural_encoding as se
from research import run_structural_experiments as runner
ROOT=Path.cwd();OUT=ROOT/'results/phase2_structural_encoding/lead_review_20260923'
records=json.loads((ROOT/'plan/phase2/FIXTURES.json').read_text())['fixtures']
def identity(c):return json.dumps(c,sort_keys=True,separators=(',',':'))
rows=[]
for record in records:
 p=record['program'];ts=sorted(record['time_domains'],key=int);ads=sorted(record['address_domains']);oracle=set();case_calls=0
 domains=[record['time_domains'][i] for i in ts]+[record['address_domains'][v] for v in ads]
 for choice in itertools.product(*domains):
  times={int(k):v for k,v in record['fixed_times'].items()};times.update({int(k):v for k,v in zip(ts,choice[:len(ts)])})
  addresses=dict(record['fixed_addresses']);addresses.update(zip(ads,choice[len(ts):]))
  bundles=[{} for _ in range(max(times.values())+1)]
  for i,op in enumerate(p['operations']):bundles[times[i]].setdefault(machine.OP_SPECS[op['op']]['engine'],[]).append(i)
  comp={'scratch':addresses,'bundles':bundles}
  try:machine.check_compilation(p,comp)
  except machine.CompileError:continue
  for case in p['cases']:machine.check_case(p,comp,case);case_calls+=1
  oracle.add(identity(comp))
 domain=se.Domain.from_record(record)
 for codec in se.CODECS:
  bits=se.layout(domain,codec).width;decoded=set();code_count=0
  if bits<=16:
   for z in range(1<<bits):
    result=se.decode(domain,z,codec)
    if result.status==se.COMPLETE:
     decoded.add(identity(result.compilation));code_count+=1
     assert se.encode(domain,result.compilation,codec)==z
   assert decoded==oracle,(record['id'],codec)
   assert code_count==len(decoded)
  for obj in oracle:
   z=se.encode(domain,json.loads(obj),codec);back=se.decode(domain,z,codec)
   assert back.status==se.COMPLETE and identity(back.compilation)==obj
  rows.append({'fixture':record['id'],'codec':codec,'bits':bits,'oracle_objects':len(oracle),'exhausted':bits<=16,'case_checks_oracle':case_calls,'pass':True})
(OUT/'independent_oracle.json').write_text(json.dumps(rows,indent=2)+'\n')
# Fully retain all 160,000 outcomes and execute every case of every completion.
original=se.decode;current={};counts={'case_checks':0,'completed':0,'draws':0};streams=[]
with (OUT/'independent_sampling_rows.jsonl').open('w') as raw:
 def audited_decode(domain,index,codec,*args,**kwargs):
  result=original(domain,index,codec,*args,**kwargs);counts['draws']+=1
  row={**current,'index':str(index),'status':result.status,'cases_checked':0}
  if result.status==se.COMPLETE:
   counts['completed']+=1
   for case in domain.program['cases']:machine.check_case(domain.program,result.compilation,case);row['cases_checked']+=1;counts['case_checks']+=1
   row['compilation_sha256']=hashlib.sha256(identity(result.compilation).encode()).hexdigest()
  raw.write(json.dumps(row,sort_keys=True)+'\n');return result
 se.decode=audited_decode
 for name,p in runner.public_programs():
  compiled,_=dc.compile_with_report(p,optimise=False)
  domain=se.Domain.from_record(runner.whole_program_record(name,'public',p,runner.dc.derive(p),compiled))
  for stream,fn,seed in [('raw_bits',runner.raw_bit_stream,20260922),('option_paths',runner.option_path_stream,20260923)]:
   current.update(program=name,stream=stream)
   result,ids=fn(domain,'structural_rank',seed,10000,60)
   streams.append({'program':name,'stream':stream,'draws':result['attempts_drawn'],'complete':result['complete'],'distinct':len(ids),'incomplete':result['incomplete']})
 se.decode=original
payload={'counts':counts,'streams':streams,'oracle_rows':len(rows),'oracle_pass':True}
(OUT/'independent_checks.json').write_text(json.dumps(payload,indent=2)+'\n');print(json.dumps(payload,indent=2))
