import pytest
from oxparc_challenge.constraints import ConstraintSystem,LinearExpression as L,QuadraticConstraint as Q
from oxparc_challenge.row_evaluator import check_rows,check_compiled_rows
from oxparc_challenge import FIELD_PRIME as P

def test_literal_rows():
 s=ConstraintSystem(public_inputs=['x'],auxiliary_signals=['b'],constraints=[Q(L(0,{'b':1}),L(-1,{'b':1}),L(),'bit'),Q(L(0,{'x':1,'b':-1}),L(1),L(),'pack')])
 assert check_rows(s.to_dict(),{'x':1,'b':1})==[]
 assert check_rows(s.to_dict(),{'x':2,'b':2})==['bit']
 for w in ({'x':P,'b':0},{'x':0},{'x':0,'b':False},{'x':0,'b':0,'z':1}):
  with pytest.raises(ValueError): check_rows(s.to_dict(),w)
 assert check_compiled_rows({'prime':str(P),'nVars':3,'constraints':[[{'1':'1'},{'2':'1'},{'0':'6'}]]},[1,2,3])==[]
 assert check_compiled_rows({'prime':str(P),'nVars':3,'constraints':[[{'1':'1'},{'2':'1'},{'0':'6'}]]},[1,2,4])==[0]
 with pytest.raises(ValueError): check_compiled_rows({'prime':str(P),'nVars':3,'constraints':[]},[0,2,3])
