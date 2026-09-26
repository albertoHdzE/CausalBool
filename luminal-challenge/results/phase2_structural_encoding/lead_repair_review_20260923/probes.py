import contextlib, io, json, shutil, tempfile
from pathlib import Path
from unittest.mock import patch
from research import check_structural_evidence as c
from research import run_structural_experiments as r
ROOT=r.ROOT
source=ROOT/'results/phase2_structural_encoding/phase2_repair_20260923b'
out=ROOT/'results/phase2_structural_encoding/lead_repair_review_20260923'
results={}
with tempfile.TemporaryDirectory(dir=out) as td:
    copy=Path(td)/'run'
    shutil.copytree(source,copy)
    gates=json.loads((copy/'gates.json').read_text()); gates['p1']['status']='PASS'
    (copy/'gates.json').write_text(json.dumps(gates))
    m=json.loads((copy/'manifest.json').read_text()); m['stage_status']['p1']='PASS'
    (copy/'manifest.json').write_text(json.dumps(m))
    buf=io.StringIO()
    with contextlib.redirect_stdout(buf):
        code=c.main(['--run',str(copy),'--contract',str(ROOT/'plan/phase2')])
    report=json.loads(buf.getvalue())
    results['false_p1_pass']={'exit':code,'report':report}
    entered=[]
    def stub(run):
        prior=run.prior('p1'); entered.append({'coverage_met':prior['coverage_met']})
        return {}
    with patch.object(r,'RESULTS',Path(td)/'outputs'), patch.dict(r.STAGE_FUNCTIONS,{'p2':stub}),contextlib.redirect_stdout(io.StringIO()):
        code=r.main(['--stage','p2','--run-id','resume_probe','--inputs',str(copy),'--contract',str(ROOT/'plan/phase2')])
    results['import_false_p1_pass']={'exit':code,'entered':entered}
    # Isolate command/log checking: missing referenced worker log and unknown exit.
    checker=c.Checker(copy,ROOT/'plan/phase2')
    (copy/'commands.jsonl').write_text(json.dumps({'exit_code':None,'log':'logs/absent.log'})+'\n')
    checker.check_commands({'stages_run':['p0','p1'],'row_counts':{}})
    results['missing_command_log']={'findings':checker.findings}
(out/'probes.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({k:{x:y for x,y in v.items() if x!='report'} for k,v in results.items()},indent=2))
