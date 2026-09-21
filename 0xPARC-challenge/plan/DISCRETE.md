# Executable discrete contract v1
N01 owns recovery.py only: pack(values,base)->int; unpack(value,n,base)->list[int];
recover(n,oracle,*,bound=None)->list[int]. All lengths/base/bounds/digits exact
Python ints (bool prohibited), n positive, digits positive <base, bound positive.
Validate oracle exact positive integer responses, recovered digits, remainder,
and sum against first response. No bound n=1 queries [1] once.
N02 owns modular.py only: solutions(p)->lexicographic list of tuples(a,b,c,d)
by enumerate a,b,c and d=-a-b-c mod p then power checks. Bound p<=31;
cubic_identity_coefficients()->dict exponent-tuples to integer nonzero
coefficients of sum cubes +3(a+b)(a+c)(b+c) after d substitution. Implement
independent small polynomial multiplication, no symbolic package needed.
B01 then B02 own boolean.py only: frozen MAJ3Gate(operands:tuple[int,int,int]),
BooleanCircuit(n_inputs:int,gates:tuple[MAJ3Gate,...],outputs:tuple[int,...]);
validate()->self, to_json()->str, from_json(str)->circuit, structural_hash()->str.
BuildLimits(max_gates=1000000,max_subproblems=1000000,timeout_seconds=300).
ResourceLimitError for all resource failures. evaluate_boolean->list[int],
import actual apply_gate from repository index-deconvolution/src via narrow
importlib adapter (no copy). Builder algorithm MASTER.md; memoization weighted
tuples deterministic. Do not implement verify_majority: lead symbolic.py owns it.
All code under integration checkout /private/tmp/oxparc-response-v1.
Acceptance: cd 0xPARC-challenge && .venv/bin/python -m pytest tests/test_discrete.py -q
No scope changes or edits to tests/plan/shared interfaces. Return handoff including
SHA256 and commands/exits, explicitly list unexecuted checks. No commits.
