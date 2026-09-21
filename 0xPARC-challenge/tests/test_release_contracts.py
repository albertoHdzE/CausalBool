"""Acceptance boundary checks for compiled export, budgets and legacy reuse."""
import copy
import difflib
import hashlib
import subprocess
from pathlib import Path
import pytest

from oxparc_challenge.boolean import build_majority,BuildLimits,ResourceLimitError
from oxparc_challenge.circom import export_circom,compile_circuit,_version
from oxparc_challenge.gadgets import build_range


BASELINE='37dae1623295f168017789e58b08eadfe0c12aa8'
# Reused upstream sources must not drift silently. A deliberate, reviewed
# enrichment of an owner is declared here by name; anything else - any deletion,
# any modification, any undeclared addition - still fails.
DECLARED_ADDITIONS={
    'index-deconvolution/src/causalbool.py':(),
    # The cofactor primitive the symbolic deconvolution backend needs. It belongs
    # to the diagram owner, so it was added there rather than re-implemented.
    'doppel-challenge/src/doppel_challenge/repertoire_program.py':('restrict',),
}


def test_legacy_sources_unchanged():
    root=Path(__file__).resolve().parents[2]
    for rel,declared in DECLARED_ADDITIONS.items():
        original=subprocess.check_output(['git','show',f'{BASELINE}:{rel}'],cwd=root).decode()
        current=(root/rel).read_text()
        if not declared:
            assert current==original,f'{rel} changed with no declared addition'
            continue
        added=[line for line in difflib.ndiff(original.splitlines(),current.splitlines())
               if line[:2] in ('- ','? ') or line.startswith('+ ')]
        assert not any(line.startswith('- ') for line in added),f'{rel} lost lines'
        inserted=[line[2:] for line in added if line.startswith('+ ')]
        assert inserted,f'{rel} declares an addition it does not contain'
        # Every inserted line must belong to a declared new definition: the run
        # starts at its ``def`` and ends where the file returns to baseline text.
        assert any(f'def {name}(' in line for name in declared for line in inserted), \
            f'{rel} additions do not include any declared name {declared}'
        stray=[line for line in inserted
               if line.strip() and not line.startswith('        ') and not line.startswith('    def ')]
        assert not stray,f'{rel} has additions outside a declared method body: {stray[:3]}'


def test_invalid_export(tmp_path):
    system=build_range().to_dict()
    bad=copy.deepcopy(system);bad['private_inputs']=['x;bad']
    with pytest.raises(ValueError):export_circom(bad,tmp_path/'bad.circom')
    bad=copy.deepcopy(system);bad['constraints'][0]['A']['terms']['undeclared']='1'
    with pytest.raises(ValueError):export_circom(bad,tmp_path/'bad.circom')
    source=export_circom(system,tmp_path/'range.circom')
    assert '<--' not in source.read_text() and source.read_text().count('===')==65
    with pytest.raises(RuntimeError):compile_circuit(source,tmp_path,circom=tmp_path/'missing')


def test_exact_tool_version(monkeypatch):
    import oxparc_challenge.circom as m
    def reply(text,code):
        monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:subprocess.CompletedProcess([],code,text,''))
    for text,code in [('circom compiler 12.2.3',0),('circom compiler 2.2.30',0),
                      ('circom compiler 2.2.3',1),('snarkjs@0.7.6',2)]:
        reply(text,code)
        with pytest.raises(RuntimeError):_version('fake','0.7.6' if 'snarkjs' in text else '2.2.3')
    reply('snarkjs@0.7.6',99);assert _version('fake','0.7.6')['exit']==99


def test_majority_resource_boundaries():
    with pytest.raises(ResourceLimitError):build_majority(3,BuildLimits(timeout_seconds=0))
    with pytest.raises(ResourceLimitError):build_majority(5,BuildLimits(max_subproblems=1))
    with pytest.raises(ResourceLimitError):build_majority(2025,BuildLimits(max_subproblems=20))
    for t in (float('inf'),float('nan')):
        with pytest.raises(ValueError):build_majority(3,BuildLimits(timeout_seconds=t))
