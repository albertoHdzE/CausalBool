"""Acceptance boundary checks for compiled export, budgets and legacy reuse."""
import copy
import hashlib
import subprocess
from pathlib import Path
import pytest

from oxparc_challenge.boolean import build_majority,BuildLimits,ResourceLimitError
from oxparc_challenge.circom import export_circom,compile_circuit,_version
from oxparc_challenge.gadgets import build_range


def test_legacy_sources_unchanged():
    root=Path(__file__).resolve().parents[2]
    for rel in ('index-deconvolution/src/causalbool.py',
                'doppel-challenge/src/doppel_challenge/repertoire_program.py'):
        original=subprocess.check_output(['git','show',f'37dae1623295f168017789e58b08eadfe0c12aa8:{rel}'],cwd=root)
        assert (root/rel).read_bytes()==original


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
