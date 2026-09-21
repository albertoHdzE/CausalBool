"""Pytest plugin retaining exact collected IDs and per-test outcomes."""
import json
import hashlib
import os
from pathlib import Path
import sys

_checks={}

def _serialisable(params):
    """Record a test's parameters without letting their type break the record.

    Parameters are whatever a test was parametrised with, so they may be any
    object at all. A structured test-evidence file must not fail to write
    because one of them is not JSON.
    """
    out={}
    for name,value in dict(params).items():
        out[name]=value if isinstance(value,(str,int,float,bool,type(None))) else repr(value)
    return out

def pytest_collection_finish(session):
    for item in session.items:
        name=item.nodeid
        if 'fourier' in name:requirements=['Q3']
        elif 'symbolic' in name or 'majority' in name or 'boolean' in name or 'naive' in name or 'gate_free' in name:requirements=['Q2']
        elif 'modular' in name:requirements=['Q4']
        elif 'factor4096' in name or 'overflow' in name:requirements=['Q8']
        elif 'factor64' in name:requirements=['Q7']
        elif 'inverse' in name:requirements=['Q6']
        elif 'range' in name:requirements=['Q5']
        elif 'test_discrete' in name:requirements=['Q1']
        else:requirements=['integration']
        _checks[item.nodeid]={'test_id':name,'requirement_ids':requirements,'status':'UNKNOWN','elapsed_seconds':0,
            'test_source_sha256':hashlib.sha256(Path(item.path).read_bytes()).hexdigest(),
            'implementation_hashes':'release.json#/source_sha256',
            'parameters':_serialisable(getattr(getattr(item,'callspec',None),'params',{})),
            'comparison':'numerical' if 'fourier' in name else 'exact',
            'tolerance':1e-10 if 'fourier' in name else None,
            'command':[sys.executable,*sys.argv], 'resource_record':'release.json#/checks'}

def pytest_runtest_logreport(report):
    check=_checks.setdefault(report.nodeid,{'test_id':report.nodeid,'status':'UNKNOWN','elapsed_seconds':0})
    check['elapsed_seconds']+=report.duration
    if report.failed:check.update(status='FAIL',detail=str(report.longrepr))
    elif report.skipped:check.update(status='UNKNOWN',detail=str(report.longrepr))
    elif report.when=='call' and check['status']=='UNKNOWN':check['status']='PASS'

def pytest_sessionfinish(session,exitstatus):
    target=os.environ.get('OXPARC_PYTEST_EVIDENCE')
    if target:
        for check in _checks.values():check['exit_code']=0 if check['status']=='PASS' else 1
        Path(target).write_text(json.dumps({'exit_code':int(exitstatus),'collected':len(_checks),
                                         'checks':list(_checks.values())},indent=2)+'\n')
