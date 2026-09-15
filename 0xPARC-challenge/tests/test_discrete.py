"""Lead-owned A-Q1, A-Q2, A-Q4 acceptance fixtures."""
import itertools
import pytest
from oxparc_challenge.recovery import recover, pack, unpack
from oxparc_challenge.boolean import BooleanCircuit, MAJ3Gate, BuildLimits, build_majority, evaluate_boolean, ResourceLimitError
from oxparc_challenge.modular import solutions, cubic_identity_coefficients

@pytest.mark.parametrize('n',[1,2,16,128])
def test_recovery(n):
    for values in ([1]*n,[2**140+7]*n,[1]*(n-1)+[2**300],list(range(1,n+1))):
        for bound in (None,max(values)):
            calls=[]
            def oracle(query):
                calls.append(query)
                assert len(query)==n and all(type(x) is int for x in query)
                return sum(a*b for a,b in zip(query,values))
            assert recover(n,oracle,bound=bound)==list(values)
            assert len(calls)==(1 if bound is not None or n==1 else 2)
            assert unpack(pack(values,max(values)+1),n,max(values)+1)==list(values)

@pytest.mark.parametrize('n',[0,-1,2.0,True])
def test_recovery_bad_length(n):
    with pytest.raises(ValueError): recover(n,lambda q:1)

@pytest.mark.parametrize('bad',[0,-1,1.5,True])
def test_recovery_bad_bound(bad):
    with pytest.raises(ValueError): recover(2,lambda q:1,bound=bad)

@pytest.mark.parametrize('bad',[0,-1,1.5,True])
def test_recovery_bad_response(bad):
    with pytest.raises(ValueError): recover(2,lambda q:bad)

@pytest.mark.parametrize('values',[[0],[1,-1],[True],[1.5],[]])
def test_pack_bad(values):
    with pytest.raises(ValueError): pack(values,10)

def test_pack_overflow():
    with pytest.raises(ValueError): pack([10],10)
    with pytest.raises(ValueError): unpack(100,1,10)

@pytest.mark.parametrize('n',[1,3,5,7,9,11])
def test_exhaustive_majority(n):
    c=build_majority(n,BuildLimits())
    c.validate()
    assert c.to_json()==build_majority(n,BuildLimits()).to_json()
    assert BooleanCircuit.from_json(c.to_json())==c
    for i,g in enumerate(c.gates):
        assert type(g) is MAJ3Gate and len(g.operands)==3
        assert all(type(r) is int and 0<=r<n+i for r in g.operands)
    for bits in itertools.product((0,1),repeat=n):
        assert evaluate_boolean(c,bits)==[int(sum(bits)>n//2)]

def test_boolean_boundary():
    c=BooleanCircuit(3,(MAJ3Gate((0,0,1)),MAJ3Gate((3,2,3))),(3,4))
    assert evaluate_boolean(c,[1,0,0])==[1,1]
    for ref in (-1,4,True):
        with pytest.raises(ValueError): BooleanCircuit(3,(MAJ3Gate((0,1,ref)),),(3,)).validate()
    for n in (0,2,-1,3.0,True):
        with pytest.raises(ValueError): build_majority(n,BuildLimits())
    with pytest.raises(ResourceLimitError): build_majority(5,BuildLimits(max_gates=0))
    with pytest.raises(ValueError): evaluate_boolean(c,[2,0,0])

def test_naive_counterexample():
    c=BooleanCircuit(9,tuple(MAJ3Gate(t) for t in [(0,1,2),(3,4,5),(6,7,8),(9,10,11)]),(12,))
    bits=[1,1,0,1,1,0,0,0,0]
    assert evaluate_boolean(c,bits)==[1] and sum(bits)<5

def test_modular():
    assert cubic_identity_coefficients()=={}
    for p in (7,11,19): assert solutions(p)==[(0,0,0,0)]
    for p in (3,5,13): assert len(solutions(p))>1

def test_modular_independent_enumeration():
 for p in (3,5,7,11,13,19):
  actual=solutions(p)
  expected=[]
  for a,b,c in itertools.product(range(p),repeat=3):
   d=(-a-b-c)%p
   if all(sum(pow(x,k,p) for x in (a,b,c,d))%p==0 for k in (1,2,3)):
    expected.append((a,b,c,d))
  assert actual==expected

def test_little_endian_packing():
 assert pack([2,3,4],10)==432
 assert unpack(432,3,10)==[2,3,4]

def test_gate_free_resource_boundary():
 assert evaluate_boolean(build_majority(1,BuildLimits(max_gates=0)),[1])==[1]
 for data in ('[]','null','{"version":true}'):
  with pytest.raises(ValueError):BooleanCircuit.from_json(data)
