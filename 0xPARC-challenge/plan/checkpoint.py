"""Record lead acceptance only after the complete release runner passes."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from oxparc_challenge.release import seal,source_hashes

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    report=json.loads((ROOT/'evidence/release.json').read_text())
    if report['status']!='PASS' or set(report['requirements'].values())!={'PASS'}:
        raise SystemExit('Cannot accept incomplete release')
    if source_hashes()!=report['source_sha256']:raise SystemExit('Source changed since release')
    state_path=ROOT/'plan/STATE.json';state=json.loads(state_path.read_text())
    for name,h in state['preliminary_sha256'].items():
        if sha(ROOT.parent/name)!=h:raise SystemExit(f'Preliminary evidence changed: {name}')
    task_files={
        'P00':['requirements.lock','npm-tools.lock.json','pyproject.toml','tools/bootstrap.py'],
        'P01':['paper/response.tex','paper/response.md','plan/MASTER.md'],
        'P02':['src/oxparc_challenge/__init__.py','src/oxparc_challenge/constraints.py'],
        'N01':['src/oxparc_challenge/recovery.py','tests/test_discrete.py'],
        'N02':['src/oxparc_challenge/modular.py','tests/test_discrete.py'],
        'B01':['src/oxparc_challenge/boolean.py','tests/test_discrete.py'],
        'B02':['src/oxparc_challenge/boolean.py','tests/test_discrete.py'],
        'B03':['src/oxparc_challenge/symbolic.py','tests/test_symbolic.py','tests/test_release_contracts.py'],
        'R01':['src/oxparc_challenge/constraints.py','tests/test_rows.py'],
        'R02':['src/oxparc_challenge/row_evaluator.py','tests/test_rows.py'],
        'R03':['src/oxparc_challenge/gadgets.py','tests/test_gadgets.py'],
        'R04':['src/oxparc_challenge/gadgets.py','tests/test_gadgets.py'],
        'R05':['src/oxparc_challenge/circom.py','tests/test_release_contracts.py'],
        'R06':['src/oxparc_challenge/compiled_audit.py','evidence/compiled_audit.json'],
        'F00':['plan/FOURIER.md'],
        'F01':['src/oxparc_challenge/fourier.py','tests/test_fourier.py'],
        'F02':['src/oxparc_challenge/fourier_search.py','tests/test_fourier.py'],
        'F03':['src/oxparc_challenge/fourier_validation.py','evidence/fourier_32768_validation.json','evidence/fourier_65536_validation.json'],
        'D01':['paper/response.tex','paper/response.md','paper/results.tex','paper/response.pdf','README.md'],
        'I00':['src/oxparc_challenge/release.py','src/oxparc_challenge/__main__.py',
               'src/oxparc_challenge/pytest_evidence.py','tools/build_paper.py','evidence/release.json'],
    }
    commands={
        'P00':'python3.13 tools/bootstrap.py',
        'P01':'PYTHONPATH=src .venv/bin/python -m oxparc_challenge verify-release',
        'P02':'.venv/bin/python -m pytest tests -q',
        'B03':'.venv/bin/python -m pytest tests/test_symbolic.py tests/test_release_contracts.py -q',
        'R06':'PYTHONPATH=src .venv/bin/python -m oxparc_challenge.compiled_audit evidence .build/compiled',
        'F00':'.venv/bin/python -m pytest tests/test_fourier.py -q',
        'F03':'PYTHONPATH=src .venv/bin/python -m oxparc_challenge verify-release',
        'D01':'.venv/bin/python tools/build_paper.py',
        'I00':'PYTHONPATH=src .venv/bin/python -m oxparc_challenge verify-release',
    }
    for tid in ('N01','N02','B01','B02'):commands[tid]='.venv/bin/python -m pytest tests/test_discrete.py -q'
    for tid in ('R01','R02'):commands[tid]='.venv/bin/python -m pytest tests/test_rows.py -q'
    for tid in ('R03','R04'):commands[tid]='.venv/bin/python -m pytest tests/test_gadgets.py -q'
    commands['R05']=commands['R06']
    for tid in ('F01','F02'):commands[tid]=commands['F00']
    for tid,files in task_files.items():
        previous=dict(state['tasks'][tid])
        state['tasks'][tid].update(status='accepted',accepted_by='lead',
            accepted_file_sha256={name:sha(ROOT/name) for name in files},acceptance_command=commands[tid])
        state['tasks'][tid].pop('sha256',None)
        state['tasks'][tid]['submission_history']=previous.get('submission_history',
            {'status':previous['status'],'reported_sha256':previous.get('sha256'),
             'note':'Historical handoff; final hashes are accepted_file_sha256. See LEAD_REVIEW.md.'})
    state['tasks']['R01']['owner']='lead'
    for tid in ('F01','F02'):state['tasks'][tid]['execution']='lead implementation; Luna review; lead final acceptance'
    state.update(release_status='PASS',next_runnable_tasks=[],blockers=[],
                 accepted_revisions={k:v['accepted_file_sha256'] for k,v in state['tasks'].items()},
                 final_environment=report['environment'],
                 reproduction_command=report['command'],
                 deferred_followups=['actual ZK proofs','CKKS ciphertext benchmarks','2025-input circuit materialization'],
                 review_record='plan/LEAD_REVIEW.md')
    state_path.write_text(json.dumps(state,indent=2)+'\n')
    tasks_path=ROOT/'plan/TASKS.yaml';tasks=json.loads(tasks_path.read_text())
    for card in tasks['tasks']:
        tid=card['task_id'];files=task_files[tid]
        ids=card['requirement_ids']
        if len(ids)==2 and ids[0].startswith('Q') and ids[1].startswith('Q'):
            card['requirement_ids']=[f'Q{i}' for i in range(int(ids[0][1:]),int(ids[1][1:])+1)]
        card['exact_test_commands']=[commands[tid]]
        card['owner_role']='lead' if state['tasks'][tid]['owner']=='lead' else 'Luna worker'
        card['execution_record']=state['tasks'][tid].get('execution',state['tasks'][tid]['owner'])
        card['accepted_artifacts']=files
        card['reviewed_revision']=state['tasks'][tid]['accepted_file_sha256']
        card['handoff_evidence']='evidence/release.json; plan/LEAD_REVIEW.md'
        card['final_acceptance']='All relevant required gates passed; lead-reviewed mathematical arguments in paper/response.tex.'
    tasks_path.write_text(json.dumps(tasks,indent=2)+'\n')
    count=seal();print(f'Lead accepted all 20 task records; sealed {count} files')

if __name__=='__main__':main()
