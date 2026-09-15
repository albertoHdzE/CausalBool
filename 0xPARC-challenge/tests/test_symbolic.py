import pytest
from oxparc_challenge.boolean import build_majority,BooleanCircuit,MAJ3Gate
from oxparc_challenge.symbolic import compile_boolean,verify_majority,ProgramLimits

@pytest.mark.parametrize('n',[13,15])
def test_exact_symbolic(n):
 c=build_majority(n)
 assert verify_majority(c)['status']=='PASS'
 bad=BooleanCircuit(c.n_inputs,c.gates,(0,))
 assert verify_majority(bad)['status']=='FAIL'

def test_symbolic_resource():
 assert verify_majority(build_majority(3),ProgramLimits(max_nodes=0))['status']=='UNKNOWN'

def test_arbitrary_outputs():
 c=BooleanCircuit(3,(MAJ3Gate((0,0,1)),),(0,1,3,2))
 p=compile_boolean(c)
 assert len(p.outputs)==4
