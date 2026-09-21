import numpy as np
import pytest
from oxparc_challenge.fourier import build_fourier,evaluate_packed,circuit_counts,coefficient_vector
from oxparc_challenge.fourier_search import search,support

@pytest.mark.parametrize('n',[2,4,8,16,32,64,128])
def test_all_basis_direct(n):
 c=build_fourier(n);j=np.arange(n)
 for k in range(n):
  x=np.zeros(n);x[k]=1
  assert np.max(np.abs(evaluate_packed(c,x)-np.exp(-2j*np.pi*j*k/n)))<1e-10

@pytest.mark.parametrize('n',[512,1024])
def test_mid_size(n):
 c=build_fourier(n);rng=np.random.default_rng(301);x=rng.normal(size=n)+1j*rng.normal(size=n)
 assert np.max(abs(evaluate_packed(c,x)-np.fft.fft(x)))/max(1,np.max(abs(np.fft.fft(x))))<1e-10

def test_mutation_controls():
 c=build_fourier(32);x=np.random.default_rng(41).normal(size=32)
 for control in ('rotation_sign','omit_bit_reversal','wrong_twiddle'):
  assert np.max(abs(evaluate_packed(c,x,**{control:-1 if control=='rotation_sign' else True})-np.fft.fft(x)))>1e-4

@pytest.mark.parametrize('n,expected',[(32768,106),(65536,121)])
def test_complete_ledger(n,expected):
 s=search(n);assert len(s['ledger'])==expected
 assert all(r['status']=='PASS' and all(c['status']=='PASS' for b in r['blocks'] for c in b['candidates']) for r in s['ledger'])
 counts=circuit_counts(build_fourier(n))
 for k in ('cost_us','multiplications','rotations','additions'):assert counts[k]==s['selected'][k]
 assert counts['depth']<=3 and counts['cost_us']<s['dense_baseline']['cost_us']

def test_support_exact_small():
 for n in (4,8,16,32):
  l=n.bit_length()-1
  for a in range(l):
   for b in range(a+1,l+1):
    for final in ((False,True) if b==l else (False,)):
     actual={k for k in range(n) if np.any(abs(coefficient_vector(n,(a,b,final,k,0)))>1e-12)}
     assert actual==set(support(n,a,b,final))
