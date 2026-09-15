"""Full-size explicit-DAG validation, evidence written after each case."""
from pathlib import Path
import hashlib
import json
import resource
import signal
import sys
import time
import numpy as np
from .fourier import build_fourier,evaluate_packed,circuit_counts
from .fourier_search import search

def vectors(n):
 yield 'zero',None,np.zeros(n,dtype=complex)
 yield 'constant',None,np.ones(n,dtype=complex)*(2-3j)
 for k in (0,1,n//3,n-1):
  x=np.zeros(n,dtype=complex);x[k]=1-2j
  yield f'impulse_{k}',None,x
 for k in (1,n//4,n-1):
  yield f'mode_{k}',None,np.exp((2j*np.pi/n)*((k*np.arange(n,dtype=np.int64))%n))
 for seed in (101,202,303,404):
  rng=np.random.default_rng(seed)
  yield 'random',seed,rng.normal(size=n)+1j*rng.normal(size=n)

def run(n,directory):
 directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
 command=f'python -m oxparc_challenge.fourier_validation {n} {directory}'
 ledger=search(n);c=build_fourier(n);counts=circuit_counts(c)
 (directory/f'fourier_{n}_ledger.json').write_text(json.dumps(ledger,indent=2)+'\n')
 # Explicit DAG retained compressed: descriptors fully specify known vectors.
 import gzip
 payload=json.dumps(c.to_dict(),sort_keys=True,separators=(',',':')).encode()
 with open(directory/f'fourier_{n}_circuit.json.gz','wb') as stream:
  with gzip.GzipFile(fileobj=stream,mode='wb',mtime=0) as zipped:zipped.write(payload)
 source=Path(__file__).parent
 hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (source/'fourier.py',source/'fourier_search.py',Path(__file__))}
 report={'requirement':'Q3','n':n,'command':command,'source_sha256':hashes,'circuit_sha256':c.structural_hash(),'counts':counts,'checks':[],'status':'UNKNOWN'}
 def save(): (directory/f'fourier_{n}_validation.json').write_text(json.dumps(report,indent=2)+'\n')
 save()
 for name,seed,x in vectors(n):
  started=time.monotonic()
  def alarm(*_):raise TimeoutError('900 second Fourier case limit')
  previous=signal.signal(signal.SIGALRM,alarm);signal.alarm(900)
  try:
   actual=evaluate_packed(c,x);expected=np.fft.fft(x)
   error=float(np.max(abs(actual-expected))/max(1,float(np.max(abs(expected)))))
   rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
   status='PASS' if np.isfinite(error) and error<=1e-10 and rss<4*1024**3 else 'FAIL'
   record={'requirement':'Q3','test_id':f'A-Q3-{n}-{name}-{seed}','status':status,'input_size':n,'seed':seed,
           'comparison':'numerical vs numpy.fft.fft','normalized_max_error':error,'tolerance':1e-10,
           'elapsed_seconds':time.monotonic()-started,'peak_rss_bytes':rss,'resource_outcome':'within limits' if rss<4*1024**3 else 'memory exceeded',
           'command':command,'exit_code':0 if status=='PASS' else 1}
  except (TimeoutError,MemoryError) as exc:
   record={'test_id':f'A-Q3-{n}-{name}-{seed}','status':'UNKNOWN','reason':str(exc),'exit_code':1,'elapsed_seconds':time.monotonic()-started}
  finally:signal.alarm(0);signal.signal(signal.SIGALRM,previous)
  report['checks'].append(record);save();print(name,seed,record,flush=True)
  if record['status']!='PASS':return 1
 report['status']='PASS';save();return 0

if __name__=='__main__':raise SystemExit(run(int(sys.argv[1]),sys.argv[2]))
