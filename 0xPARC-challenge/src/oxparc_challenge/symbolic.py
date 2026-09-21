"""Additive arbitrary MAJ3 DAG API using CausalBool's shared DD manager.

This intentionally does not call the synchronous repertoire serializer, which
requires n outputs. Neither Network nor the legacy codec is modified.
"""
from dataclasses import dataclass
from pathlib import Path
import importlib.util
import sys

_ROOT = Path(__file__).resolve().parents[3]
_PATH = _ROOT/'doppel-challenge/src/doppel_challenge/repertoire_program.py'
_spec = importlib.util.spec_from_file_location('_oxparc_shared_dd',_PATH)
_dd = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _dd
_spec.loader.exec_module(_dd)
ProgramLimits = _dd.ProgramLimits

@dataclass(frozen=True)
class SymbolicCircuit:
    n_inputs: int
    nodes: tuple
    outputs: tuple
    allocated_nodes: int


def _compose(circuit,manager):
    circuit.validate()
    refs=[manager.mk(i,0,1) for i in range(circuit.n_inputs)]
    for gate in circuit.gates:
        a,b,c=(refs[r] for r in gate.operands)
        ab=manager.apply('and',a,b)
        ac=manager.apply('and',a,c)
        bc=manager.apply('and',b,c)
        refs.append(manager.apply('or',ab,manager.apply('or',ac,bc)))
    return tuple(refs[r] for r in circuit.outputs)


def compile_boolean(circuit,limits=None):
    manager=_dd._Manager(circuit.n_inputs,limits or ProgramLimits(max_nodes=2_000_000))
    outputs=_compose(circuit,manager)
    return SymbolicCircuit(circuit.n_inputs,tuple(manager.nodes),outputs,len(manager.nodes))


def verify_majority(circuit,limits=None):
    try:
        circuit.validate()
        if circuit.n_inputs%2!=1 or len(circuit.outputs)!=1:
            return {'status':'FAIL','reason':'positive odd inputs and one output required'}
        manager=_dd._Manager(circuit.n_inputs,limits or ProgramLimits(max_nodes=2_000_000))
        roots=_compose(circuit,manager)
        # Independent threshold recurrence over external coordinates, no MAJ3 builder.
        target=manager.threshold(list(range(circuit.n_inputs)),circuit.n_inputs//2+1)
        return {'status':'PASS' if roots==(target,) else 'FAIL',
                'comparison':'exact canonical decision-node identity',
                'allocated_nodes':len(manager.nodes),'n_inputs':circuit.n_inputs}
    except (_dd.ResourceLimitError,TimeoutError) as exc:
        return {'status':'UNKNOWN','reason':str(exc)}
    except ValueError as exc:
        return {'status':'FAIL','reason':str(exc)}
