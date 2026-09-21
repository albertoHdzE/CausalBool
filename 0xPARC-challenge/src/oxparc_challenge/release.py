"""Fail-closed release runner and artifact integrity checks."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
EXCLUDED={'.venv','.tools','.build','__pycache__','.pytest_cache'}
CORE_SOURCES=('index-deconvolution/src/causalbool.py',
              'doppel-challenge/src/doppel_challenge/repertoire_program.py')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def source_hashes():
    return {str(p.relative_to(ROOT)):sha(p) for folder in ('src','tests','tools')
            for p in (ROOT/folder).rglob('*.py') if '__pycache__' not in p.parts}

def artifact_files():
    files=[p for p in ROOT.rglob('*') if p.is_file() and not set(p.relative_to(ROOT).parts)&EXCLUDED
           and not any(part.endswith('.egg-info') for part in p.relative_to(ROOT).parts)
           and p!=ROOT/'evidence/manifest.json' and p.suffix not in ('.pyc','.log','.aux','.out','.toc')]
    files.extend(ROOT.parent/p for p in CORE_SOURCES)
    files.append(ROOT.parent/'.github/workflows/oxparc.yml')
    return files

def seal():
    hashes={os.path.relpath(p,ROOT):sha(p) for p in sorted(artifact_files())}
    (ROOT/'evidence/manifest.json').write_text(json.dumps({'algorithm':'SHA256','files':hashes},indent=2)+'\n')
    return len(hashes)

def check_manifest():
    manifest=json.loads((ROOT/'evidence/manifest.json').read_text())
    bad=[name for name,h in manifest['files'].items() if not (ROOT/name).is_file() or sha(ROOT/name)!=h]
    if bad:raise RuntimeError('Artifact hash mismatch: '+', '.join(bad))
    print(f"Verified {len(manifest['files'])} artifact hashes")
    return 0

def verify_release():
    os.chdir(ROOT)
    evidence=ROOT/'evidence';evidence.mkdir(exist_ok=True)
    report={'status':'UNKNOWN','command':'PYTHONPATH=src .venv/bin/python -m oxparc_challenge verify-release',
            'source_sha256':source_hashes(),'checks':[],'requirements':{f'Q{i}':'UNKNOWN' for i in range(1,9)}}
    def save():(evidence/'release.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join([str(ROOT/'src'),str(ROOT.parent/'doppel-challenge/src')])
    def run(name,args,timeout=300,extra_env=None):
        started=time.monotonic()
        record={'test_id':name,'command':[str(a) for a in args],'status':'UNKNOWN'}
        report['checks'].append(record);save();print(name,flush=True)
        try:
            p=subprocess.run(args,cwd=ROOT,env={**env,**(extra_env or {})},capture_output=True,text=True,timeout=timeout)
            (evidence/f'{name}.log.txt').write_text(p.stdout+p.stderr)
            peak=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
            record.update(exit_code=p.returncode,elapsed_seconds=time.monotonic()-started,peak_child_rss_bytes=peak,
                          resource_outcome='within limits' if peak<4*1024**3 else 'memory budget exceeded',
                          status='PASS' if p.returncode==0 and peak<4*1024**3 else 'FAIL')
            save()
            if record['status']!='PASS':raise RuntimeError(f'{name}: {p.stdout[-1500:]} {p.stderr[-1500:]}')
            return p
        except (FileNotFoundError,subprocess.TimeoutExpired) as exc:
            record.update(status='UNKNOWN',error=str(exc),elapsed_seconds=time.monotonic()-started);save();raise
    try:
        if sys.version_info[:2]!=(3,13):raise RuntimeError('Python 3.13 required')
        locked=dict(line.split('==') for line in (ROOT/'requirements.lock').read_text().splitlines() if line.strip())
        versions={name:importlib.metadata.version(name) for name in locked}
        if versions!=locked:raise RuntimeError(f'Locked dependencies required: {versions}')
        from .circom import _version,_default_tool
        tool_versions=[_version(_default_tool('circom'),'2.2.3'),_version(_default_tool('node_modules/.bin/snarkjs'),'0.7.6')]
        report['environment']={'python':sys.version,'platform':platform.platform(),'dependencies':versions,
            'node':subprocess.check_output(['node','--version'],text=True).strip(),
            'npm':subprocess.check_output(['npm','--version'],text=True).strip(),
            'pdflatex':subprocess.check_output(['pdflatex','--version'],text=True).splitlines()[0],
            'compiler_sha256':sha(_default_tool('circom')),'tools':tool_versions,
            'requirements_lock_sha256':sha(ROOT/'requirements.lock'),'npm_lock_sha256':sha(ROOT/'npm-tools.lock.json')}
        save()
        run('acceptance',[sys.executable,'-m','pytest','-p','oxparc_challenge.pytest_evidence','tests','-q'],
            extra_env={'OXPARC_PYTEST_EVIDENCE':str(evidence/'acceptance_pytest.json')})
        acceptance=json.loads((evidence/'acceptance_pytest.json').read_text())
        required={'test_discrete.py':34,'test_fourier.py':13,'test_gadgets.py':7,
                  'test_rows.py':1,'test_symbolic.py':4,'test_release_contracts.py':4}
        for file,count in required.items():
            observed=[c for c in acceptance['checks'] if '/'+file+'::' in '/'+c['test_id']]
            if len(observed)!=count or any(c['status']!='PASS' for c in observed):
                raise RuntimeError(f'Required test collection/outcomes differ for {file}: {len(observed)} vs {count}')
        run('legacy',[sys.executable,'-m','pytest','-p','oxparc_challenge.pytest_evidence',
              '../index-deconvolution/tests/test_deconvolution.py','../doppel-challenge/tests/test_repertoire_program.py',
              '-k','not wolfram_gate_parity and not bdm_preserves_matrix_shape','-q'],
            extra_env={'OXPARC_PYTEST_EVIDENCE':str(evidence/'legacy_pytest.json')})
        legacy=json.loads((evidence/'legacy_pytest.json').read_text())
        if legacy['collected']!=525 or any(c['status']!='PASS' for c in legacy['checks']):
            raise RuntimeError('Affected legacy tests missing, skipped, or failed')
        report['legacy_exclusions']=['Wolfram backend parity (not modified)','BDM matrix backend (not used by challenge)']
        run('compiled',[sys.executable,'-m','oxparc_challenge.compiled_audit','evidence','.build/compiled'],timeout=600)
        arithmetic=json.loads((evidence/'compiled_audit.json').read_text())
        if arithmetic['status']!='PASS' or len(arithmetic['checks'])!=66 or set(arithmetic['families'])!={'Q5','Q6','Q7','Q8'}:
            raise RuntimeError('Compiled audit incomplete')
        if any(c['status']!='PASS' for c in arithmetic['checks']):raise RuntimeError('Compiled check failed')
        for n in (32768,65536):
            run(f'fourier_{n}',[sys.executable,'-m','oxparc_challenge.fourier_validation',str(n),'evidence'],timeout=900)
            data=json.loads((evidence/f'fourier_{n}_validation.json').read_text())
            if data['status']!='PASS' or len(data['checks'])!=13 or any(c['status']!='PASS' for c in data['checks']):
                raise RuntimeError(f'Full Fourier checks incomplete for {n}')
        from .discrete_evidence import generate
        generate(evidence)
        run('paper',[sys.executable,'tools/build_paper.py'])
        # Source evidence must describe exactly the code that passed.
        if report['source_sha256']!=source_hashes():raise RuntimeError('Source changed during verification')
        report['requirements']={f'Q{i}':'PASS' for i in range(1,9)}
        report['status']='PASS';save()
        count=seal();print(f'Release PASS; {count} artifacts sealed',flush=True)
        return 0
    except Exception as exc:
        report['status']='FAIL' if any(c['status']=='FAIL' for c in report['checks']) else 'UNKNOWN'
        report['error']=repr(exc);save();print(f'Release {report["status"]}: {exc}',file=sys.stderr)
        return 1
