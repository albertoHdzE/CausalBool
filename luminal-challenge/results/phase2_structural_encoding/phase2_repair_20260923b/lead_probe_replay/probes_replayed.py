from pathlib import Path
import contextlib,io,json,shutil,tempfile,sys
from unittest.mock import patch
import machine
import direct_compiler as dc
import direct_contract as facts_owner
from research import run_structural_experiments as r
from research import check_structural_evidence as ck
from research import structural_encoding as se
ROOT=Path.cwd(); OUT=ROOT/'results/phase2_structural_encoding/phase2_repair_20260923b/lead_probe_replay'
SOURCE=ROOT/'results/phase2_structural_encoding/phase2_20260922_final'
CONTRACT=ROOT/'plan/phase2'; findings={}
def checker(path):
 buf=io.StringIO()
 with contextlib.redirect_stdout(buf): code=ck.main(['--run',str(path),'--contract',str(CONTRACT)])
 result=json.loads(buf.getvalue()); return {'exit':code,'findings':result.get('findings'),'complete':result.get('artifacts_complete'),'inconclusive':result.get('inconclusive_count')}
findings['checker_control']=checker(SOURCE)
with tempfile.TemporaryDirectory(prefix='phase2-lead-') as temp:
 target=Path(temp)/'copy';shutil.copytree(SOURCE,target)
 # No re-hashing: checker should detect the altered summary against manifest.
 p=target/'p1/summary.json'; d=json.loads(p.read_text());d['fixtures']=[];d['public_coverage']=[];p.write_text(json.dumps(d))
 (target/'p1/sampling_streams.jsonl').write_text('')
 gates=json.loads((target/'gates.json').read_text());gates['p1']['status']='PASS';(target/'gates.json').write_text(json.dumps(gates))
 for name in ('decoder_rows.jsonl','oracle_domains.jsonl'):(target/'p1'/name).unlink()
 findings['checker_empty_p1']=checker(target)
# Constant legal domain, make case execution observably fail if called.
record=json.loads((CONTRACT/'FIXTURES.json').read_text())['fixtures'][0]
record=json.loads(json.dumps(record)); inc=record['incumbent']
times={str(i):t for t,b in enumerate(inc['bundles']) for ids in b.values() for i in ids}
for key in record['time_domains']:record['time_domains'][key]=[times[key]]
for key in record['address_domains']:record['address_domains'][key]=[inc['scratch'][key]]
domain=se.Domain.from_record(record)
with patch.object(machine,'check_case',side_effect=AssertionError('case validator invoked')) as case:
 stream,_=r.raw_bit_stream(domain,'structural_rank',20260922,3,10)
 findings['sampler_case_validation']={'complete':stream['complete'],'case_calls':case.call_count,'retained_examples':len(stream['complete_examples'])}
# Verify resuming can enter P2 on an INCONCLUSIVE P1 without running real P2.
entered=[]
def dummy_p2(run):
 prior=run.prior('p1'); entered.append(prior['coverage_met']); return {'stage':'p2','review_probe_only':True}
with tempfile.TemporaryDirectory(prefix='phase2-resume-', dir=OUT) as temp, patch.object(r,'RESULTS',Path(temp)),patch.dict(r.STAGE_FUNCTIONS,{'p2':dummy_p2}):
 with contextlib.redirect_stdout(io.StringIO()):code=r.main(['--stage','p2','--run-id','probe','--contract',str(CONTRACT),'--inputs',str(SOURCE)])
 findings['resume_gate_bypass']={'exit':code,'entered_p2_with_prior_coverage':entered}
# Passed construction time must debit remaining search budget.
p=machine.load_program(ROOT/'.reference/programs/02_scalar_dual_chain.json'); compiled,_=dc.compile_with_report(p,optimise=False);facts=facts_owner.derive(p)
times=se.issue_cycles_of(p,compiled['bundles']);addresses=compiled['scratch'];limits=json.loads((CONTRACT/'PROTOCOL.json').read_text())['budgets']
clock=[0.0]; original=r.matched_window_record; captured=[]
class ReachedSearch(Exception):pass
def slow_construction(*a,**kw):
 result=original(*a,**kw);clock[0]+=1.0;return result
def capture_search(domain,incumbent,arm,budget):
 captured.append({'clock_at_search':clock[0],'budget_seconds':budget.seconds});raise ReachedSearch
with patch.object(r.time,'perf_counter',side_effect=lambda:clock[0]),patch.object(r,'matched_window_record',side_effect=slow_construction),patch.object(r.ss,'search',side_effect=capture_search):
 try:r.structural_optimise(p,facts,times,addresses,'structural_bound',0.01,0.01,32,limits)
 except ReachedSearch:pass
findings['construction_budget_not_debited']={'global_budget':0.01,'calls':captured}
try:
 r.structural_optimise(p,facts,times,addresses,r.MODEL_ARM,0.1,0.1,32,limits)
 findings['conditional_model_arm']={'exception':None}
except Exception as e:findings['conditional_model_arm']={'exception':type(e).__name__,'message':str(e)}
original_digest=r.file_digest
reference_readme=ROOT/'.reference/README.md'
with patch.object(r,'file_digest',side_effect=lambda path: '0'*64 if Path(path)==reference_readme else original_digest(path)):
 findings['reference_manifest_entry_ignored']=r.Contract(CONTRACT).verify_locks()
(OUT/'probes.json').write_text(json.dumps(findings,indent=2)+'\n');print(json.dumps(findings,indent=2))
