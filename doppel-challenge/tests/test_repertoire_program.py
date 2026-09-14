import itertools
import json
from pathlib import Path
import subprocess

import pytest

from doppel_challenge.adapters import Network, GATE_TYPES, apply_gate
from doppel_challenge.full_behaviour import WOLFRAM_KERNEL, REPO_ROOT
from doppel_challenge.repertoire_program import (
    ProgramLimits, RepertoireProgram, ResourceLimitError, compile_repertoire_program,
    compile_schema_program, deserialize_program, evaluate_program, export_output_schemata,
    iter_output_rows, program_metadata, serialize_program,
)
from doppel_challenge.program_benchmark import (
    _run_isolated, bdm_output_matrix, mixed_cases, run_program_benchmark,
    validate_program_benchmark,
)


def gate_specs():
    specs = []
    for d in range(1, 7):
        for gate in GATE_TYPES:
            if gate in ("IMPLIES", "NIMPLIES") and d < 2:
                continue
            params = [{}]
            if gate == "KOFN":
                params = [{"k": k, "strict": strict} for k in range(-1, d+2) for strict in (False, True)]
            if gate == "MAJORITY":
                params = [{"tiePolicy": p} for p in ("strict", "atOrAbove")]
            if gate == "CANALISING":
                params = [{"canalisingIndex": i, "canalisingValue": v, "canalisedOutput": out}
                          for i in range(d) for v in (0, 1) for out in (0, 1)]
            specs.extend((d, gate, p) for p in params)
    return specs


@pytest.mark.parametrize("function", range(256))
def test_every_three_input_function(function):
    schemata = [(x, 0) for x in range(8) if function >> x & 1]
    p = compile_schema_program(3, [schemata]*3)
    decoded = deserialize_program(serialize_program(p), n=3)
    assert list(iter_output_rows(decoded)) == [[function >> x & 1]*3 for x in range(8)]
    assert serialize_program(compile_schema_program(3, [list(reversed(schemata))]*3)) == serialize_program(p)


@pytest.mark.parametrize("d,gate,params", gate_specs())
def test_parameterized_gates(d, gate, params):
    # Noncontiguous supports pin coordinate transport as well as truth values.
    n = d+1
    support = [i for i in range(n) if i != n//2]
    net = Network(n, [[int(i in support) for i in range(n)]]*n, [gate]*n, [params]*n)
    p = compile_repertoire_program(net)
    decoded = deserialize_program(serialize_program(p), n=n)
    expected = [[apply_gate(gate, [(x >> i) & 1 for i in support], params)]*n for x in range(1 << n)]
    assert list(iter_output_rows(decoded)) == expected
    assert serialize_program(compile_repertoire_program(net, division_size=n)) == serialize_program(p)


def test_wolfram_gate_parity():
    if not Path(WOLFRAM_KERNEL).exists():
        pytest.skip("Wolfram unavailable; release requires this check")
    cases = []
    for n, gate, params in gate_specs():
        net = Network(n, [[1]*n]*n, [gate]*n, [params]*n)
        p = compile_repertoire_program(net)
        wp = dict(params)
        if "canalisingIndex" in wp:
            wp["canalisingIndex"] += 1
        cases.append({"n": n, "gate": gate, "params": wp,
                      "expected": [row[0] for row in iter_output_rows(p)]})
    payload = json.dumps(cases)
    code = ('Get["src/Packages/Integration/Gates.m"]; c=ImportString[' + json.dumps(payload) + ',"RawJSON"];'
            'checks=Table[Table[Integration`Gates`ApplyGate[a["gate"],Reverse[IntegerDigits[x,2,a["n"]]],a["params"]],'
            '{x,0,2^a["n"]-1}]===a["expected"],{a,c}];'
            'WriteString["stdout",ExportString[checks,"RawJSON"]];Exit[]')
    result = subprocess.run([WOLFRAM_KERNEL, "-noprompt", "-run", code], cwd=REPO_ROOT,
                            text=True, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stderr
    checks = json.loads(result.stdout)
    assert len(checks) == 226 and all(checks)


def test_mixed_networks_and_disjoint_schemata():
    for case in mixed_cases():
        n = case["network_size"]
        net = Network(n, case["cm"], case["dyn"], case["params"])
        program = compile_repertoire_program(net)
        restored = deserialize_program(serialize_program(program), n=n)
        sets = []
        for j in range(n):
            seen = set()
            for anchor, free in export_output_schemata(restored, j):
                offset = free
                while True:
                    assert anchor + offset not in seen
                    seen.add(anchor + offset)
                    if offset == 0:
                        break
                    offset = (offset-1) & free
            sets.append(seen)
        for x, row in enumerate(iter_output_rows(restored)):
            expected = [apply_gate(gate, [(x >> i) & 1 for i, b in enumerate(cm) if b], params)
                        for gate, cm, params in zip(net.gates, net.C, net.params)]
            assert row == expected == [int(x in ones) for ones in sets]


def test_compilation_does_not_enumerate(monkeypatch):
    import doppel_challenge.adapters as a
    import doppel_challenge.compression as c
    def forbidden(*args, **kwargs):
        raise AssertionError("exhaustive helper called during compilation")
    for name in ("apply_gate", "truth_table", "repertoire", "node_output_column", "minimal_dnf"):
        monkeypatch.setattr(a, name, forbidden)
    monkeypatch.setattr(c, "unfold_decimal_sumandos", forbidden)
    n = 100
    for gate in GATE_TYPES:
        p = compile_repertoire_program(Network(n, [[1]*n]*n, [gate]*n))
        assert len(p.nodes) < 3000
        assert len(serialize_program(p)) < 12000


def test_free_connected_coordinates_and_shared_outputs():
    net = Network(3, [[1, 1, 0]]*3, ["OR"]*3)
    p = compile_repertoire_program(net)
    assert export_output_schemata(p, 0) == [(2, 4), (1, 6)]
    assert len(set(p.outputs)) == 1
    # Overlap is a union, never an occurrence-count multiplication.
    overlap = compile_schema_program(3, [[(1, 6), (2, 5)]]*3)
    assert serialize_program(p) == serialize_program(overlap)


def test_long_decision_paths_are_iterative():
    n = 1500
    p = compile_schema_program(n, [[(0, 0)]] + [[] for _ in range(n-1)])
    restored = deserialize_program(serialize_program(p), n=n)
    assert evaluate_program(restored, 0) == [1] + [0]*(n-1)
    assert evaluate_program(restored, 1) == [0]*n
    assert export_output_schemata(restored, 0) == [(0, 0)]


@pytest.mark.parametrize("gate", ["AND", "OR", "XOR", "NAND", "NOR", "XNOR", "MAJORITY", "KOFN"])
def test_empty_support_and_single_coordinate(gate):
    p = compile_repertoire_program(Network(1, [[0]], [gate]))
    q = deserialize_program(serialize_program(p), n=1)
    assert list(iter_output_rows(q)) == [[apply_gate(gate, [])]]*2


def test_limits_and_invalid_inputs():
    net = Network(3, [[1]*3]*3, ["XOR"]*3)
    with pytest.raises(ResourceLimitError):
        compile_repertoire_program(net, limits=ProgramLimits(max_nodes=1))
    p = compile_repertoire_program(net)
    with pytest.raises(ResourceLimitError):
        export_output_schemata(p, 0, max_schemata=1)
    for gate, params in (("CUSTOM", {}), ("OR", {"noiseFlipProb": .1}),
                         ("KOFN", {"strict": 1}), ("CANALISING", {"canalisingIndex": 5})):
        with pytest.raises(ValueError):
            compile_repertoire_program(Network(3, [[1]*3]*3, [gate]*3, [params]*3))
    with pytest.raises(ValueError):
        compile_schema_program(1, [[(1, 1)]])


def test_binary_format_lengths_and_rejections():
    p = compile_schema_program(1, [[(1, 0)]])
    # gamma(2)=010, no coordinate bits, child refs 00/10, output 01 (LSB fields).
    assert serialize_program(p) == bytes([0b01000100, 0b10000000])
    info = program_metadata(p)
    assert info["program_bit_length"] == 9
    assert info["padding_bits"] == 7
    payload = serialize_program(p)
    for bad in (b"", b"\x00", payload[:-1], payload+b"\x00", payload[:-1]+b"\x81"):
        with pytest.raises(ValueError):
            deserialize_program(bad, n=1)
    for nodes, roots in ((((0, 2, 1),), (2,)), (((0, 0, 0),), (2,)),
                         (((0, 0, 1), (0, 0, 1)), (3,))):
        with pytest.raises(ValueError):
            serialize_program(RepertoireProgram(1, nodes, roots))
    assert program_metadata(deserialize_program(payload, n=1))["canonical_program_sha256"] == info["canonical_program_sha256"]


def test_bdm_preserves_matrix_shape():
    result = bdm_output_matrix([[0]*10 for _ in range(8)])
    assert result["status"] == "completed"
    assert result["provenance"]["original_shape"] == [8, 10]
    assert result["provenance"]["padded_shape"] == [8, 12]
    assert result["provenance"]["padding_bits"] == 16


def test_worker_failure_taxonomy(monkeypatch):
    import doppel_challenge.program_benchmark as b
    case = {"label": "test", "network_size": 1, "cm": [[1]], "dyn": ["AND"]}
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("worker", 1)
    monkeypatch.setattr(b.subprocess, "run", timeout)
    assert _run_isolated(case)["status"] == "timeout"
    monkeypatch.setattr(b.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 1, "", "crash"))
    assert _run_isolated(case)["status"] == "compiler_failure"
    monkeypatch.setattr(b.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 0, "{}", ""))
    assert _run_isolated(case)["status"] == "malformed_payload"


def test_benchmark_resource_failure_is_not_success():
    case = {"label": "test", "network_size": 3, "cm": [[1]*3]*3, "dyn": ["XOR"]*3}
    record = run_program_benchmark([case], include_large=False, verify_wolfram=False, max_nodes=1)
    assert not record["accepted_validation"] and not record["release_ready"]
    assert record["cases"][0]["status"] == "resource_exhaustion"
    assert validate_program_benchmark(record)["valid"]


def test_scientific_digest_excludes_worker_timing():
    from doppel_challenge.records import scientific_digest
    a = {"record_kind": "shared_program_benchmark", "cases": [{"compile_seconds": 1,
         "serialization_seconds": 2, "decode_and_reference_validation_seconds": 3,
         "program_bit_length": 40}]}
    b = {"record_kind": "shared_program_benchmark", "cases": [{"compile_seconds": 10,
         "serialization_seconds": 20, "decode_and_reference_validation_seconds": 30,
         "program_bit_length": 40}]}
    assert scientific_digest(a) == scientific_digest(b)
    b["cases"][0]["program_bit_length"] = 41
    assert scientific_digest(a) != scientific_digest(b)


def test_noncanonical_or_malformed_binary_graph():
    # An independent writer deliberately bypasses all production validation.
    def raw(n, nodes, roots):
        m = len(nodes)
        gamma = bin(m+1)[2:]
        bits = '0'*(len(gamma)-1)+gamma
        vw, rw = (n-1).bit_length(), (m+1).bit_length()
        def field(v, w):
            return format(v, f'0{w}b')[::-1] if w else ''
        for v, lo, hi in nodes:
            bits += field(v, vw)+field(lo, rw)+field(hi, rw)
        bits += ''.join(field(r, rw) for r in roots)
        bits += '0'*(-len(bits) % 8)
        return bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))
    for n, nodes, roots in (
        (1, [(0, 2, 1)], [2]),  # self reference
        (1, [(0, 0, 1)], [3]),  # bad output
        (1, [(0, 0, 1)], [0]),  # unreachable
        (1, [(0, 0, 0)], [2]),  # redundant
        (2, [(0, 0, 1), (1, 0, 2)], [3, 2]),  # variable order
        (2, [(0, 0, 1), (1, 0, 1)], [3, 2]),  # noncanonical numbering
        (1, [(0, 0, 1), (0, 0, 1)], [3]),  # duplicate
    ):
        with pytest.raises(ValueError):
            deserialize_program(raw(n, nodes, roots), n=n)


def test_reference_owner_failure_classes(monkeypatch):
    import doppel_challenge.program_benchmark as b
    case = {"label": "test", "network_size": 1, "cm": [[1]], "dyn": ["AND"]}
    def timeout(*a, **k):
        raise subprocess.TimeoutExpired('wolfram', 1)
    monkeypatch.setattr(b.subprocess, 'run', timeout)
    assert b.wolfram_reference(case)['status'] == 'timeout'
    monkeypatch.setattr(b.subprocess, 'run', lambda *a, **k: subprocess.CompletedProcess([], 1, '', 'failed'))
    assert b.wolfram_reference(case)['status'] == 'process_failure'
    monkeypatch.setattr(b.subprocess, 'run', lambda *a, **k: subprocess.CompletedProcess([], 0, 'bad json', ''))
    assert b.wolfram_reference(case)['status'] == 'malformed_payload'
    monkeypatch.setattr(b.subprocess, 'run', lambda *a, **k: subprocess.CompletedProcess([], 0, '[[0],[1]]', ''))
    assert b.wolfram_reference(case)['process_status'] == 'normal_exit'


def test_reference_mismatch_blocks_release(monkeypatch):
    import doppel_challenge.program_benchmark as b
    case = {"label": "test", "network_size": 1, "cm": [[1]], "dyn": ["AND"]}
    monkeypatch.setattr(b, 'wolfram_reference', lambda *a, **k: {'status': 'completed', 'output_sha256': 'wrong'})
    record = b.run_program_benchmark([case], include_large=False)
    assert record['cases'][0]['status'] == 'reconstruction_mismatch'
    assert not record['accepted_validation'] and not record['release_ready']
