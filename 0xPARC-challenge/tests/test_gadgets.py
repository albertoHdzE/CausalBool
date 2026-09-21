import pytest
from oxparc_challenge import FIELD_PRIME as P
from oxparc_challenge.gadgets import build_range, witness_range, build_exclude_one, witness_exclude_one, build_factor64, witness_factor64, build_factor4096, witness_factor4096
from oxparc_challenge.row_evaluator import check_rows

def test_range():
 s=build_range()
 for x in (0,1,2**64-1): assert check_rows(s.to_dict(),witness_range(x))==[]
 for x in (2**64,P-1):
  w=witness_range(0);w['x']=x
  assert check_rows(s.to_dict(),w)
 w=witness_range(0);w['x']=2;w['x_b0']=2
 assert check_rows(s.to_dict(),w)
 for x in (-1,P,True):
  with pytest.raises(ValueError): witness_range(x)

def test_inverse():
 s=build_exclude_one()
 for r in (0,2,P-1): assert check_rows(s.to_dict(),witness_exclude_one(r))==[]
 w={'r':1,'s':0};assert check_rows(s.to_dict(),w)

def test_factor64():
 s=build_factor64().to_dict()
 for u,v in ((2,3),(3,2),(65537,65539),(2,(2**64-2)//2)):
  w=witness_factor64(u*v,u,v);assert check_rows(s,w)==[]
  w['n']+=1; assert check_rows(s,w)
 for u,v in ((0,0),(1,6),(6,1)):
  with pytest.raises(ValueError): witness_factor64(u*v,u,v)

@pytest.mark.parametrize('u,v',[(2**2047+123,2**2047+321),(2,2**4094+1),(2**4094+1,2)])
def test_factor4096(u,v):
 s=build_factor4096().to_dict();w=witness_factor4096(u*v,u,v)
 assert check_rows(s,w)==[]
 for name in ('q_0_0','carry_1','carry_0','carry_128','n_63','u_63'):
  bad=dict(w);bad[name]=(bad[name]+1)%P
  assert check_rows(s,bad),name
 assert len([x for x in s['constraints'] if x['label'].startswith('partial_')])==4096

def test_overflow():
 with pytest.raises(ValueError): witness_factor4096(0,2**4095,2)
