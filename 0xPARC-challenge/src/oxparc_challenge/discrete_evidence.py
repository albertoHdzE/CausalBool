"""Record emitted majority circuits and exact modular examples."""
import gzip
import hashlib
import json
from pathlib import Path
import time
from .boolean import build_majority
from .symbolic import verify_majority
from .modular import solutions,cubic_identity_coefficients

def generate(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    output={'command':'python -m oxparc_challenge verify-release','status':'UNKNOWN',
            'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in Path(__file__).parent.glob('*.py')},'majority':[],'modular':[]}
    for n in (1,3,5,7,9,11,13,15):
        start=time.monotonic();c=build_majority(n);check=verify_majority(c)
        if check['status']!='PASS':raise RuntimeError(check)
        record={'test_id':f'A-Q2-emitted-{n}','n':n,'gates':len(c.gates),
                'sha256':c.structural_hash(),'elapsed_seconds':time.monotonic()-start,**check}
        output['majority'].append(record)
        path=directory/f'majority_{n}.json.gz'
        with open(path,'wb') as stream:
            with gzip.GzipFile(fileobj=stream,mode='wb',mtime=0) as z:z.write(c.to_json().encode())
    if cubic_identity_coefficients():raise AssertionError('cubic polynomial identity')
    for p in (3,5,7,11,13,19):
        start=time.monotonic();values=solutions(p)
        output['modular'].append({'test_id':f'A-Q4-enumerated-{p}','p':p,'solution_count':len(values),
                                  'solutions':values,'status':'PASS','elapsed_seconds':time.monotonic()-start})
    output['status']='PASS'
    (directory/'discrete.json').write_text(json.dumps(output,indent=2)+'\n')
    return output
