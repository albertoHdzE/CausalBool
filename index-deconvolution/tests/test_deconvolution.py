"""Test suite for the index-set deconvolution.

Run with:  python -m pytest tests/ -q
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from causalbool import Network, apply_gate, truth_table, repertoire, node_output_column
from deconvolution import (
    essential_variables, reduce_column, identify_gate,
    deconvolve, verify,
)
from network_generator import random_network


# ---------------------------------------------------------------------------
# Forward gate semantics (spot checks against Gates.m definitions)
# ---------------------------------------------------------------------------

def test_gate_truth_tables():
    assert truth_table("AND", 2) == [0, 0, 0, 1]
    assert truth_table("OR", 2) == [0, 1, 1, 1]
    assert truth_table("XOR", 2) == [0, 1, 1, 0]
    assert truth_table("NAND", 2) == [1, 1, 1, 0]
    assert truth_table("NOR", 2) == [1, 0, 0, 0]
    assert truth_table("XNOR", 2) == [1, 0, 0, 1]
    assert truth_table("NOT", 1) == [1, 0]
    # IMPLIES enumerated LSB-first: (0,0)->1 (1,0)->0 (0,1)->1 (1,1)->1
    assert truth_table("IMPLIES", 2) == [1, 0, 1, 1]
    assert truth_table("NIMPLIES", 2) == [0, 1, 0, 0]
    # MAJORITY of 3, ties resolve to 0 at weight 1
    assert truth_table("MAJORITY", 3) == [0, 0, 0, 1, 0, 1, 1, 1]
    assert truth_table("KOFN", 3, {"k": 2}) == [0, 0, 0, 1, 0, 1, 1, 1]


# ---------------------------------------------------------------------------
# Pivots vs sumandos: essential variables equal connected inputs
# ---------------------------------------------------------------------------

def test_essential_variables_equal_connectivity():
    # Node 0: AND of inputs {1, 3} in a 4-node network.
    n = 4
    C = [[0, 1, 0, 1], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    net = Network(n=n, C=C, gates=["AND", "FALSE", "FALSE", "FALSE"] if False else ["AND", "OR", "OR", "OR"], params=[])
    # Give the other nodes trivial single-input identities so the network is valid.
    C[1][1] = 1
    C[2][2] = 1
    C[3][3] = 1
    net = Network(n=n, C=C, gates=["AND", "OR", "OR", "OR"])
    col = node_output_column(net, 0)
    assert essential_variables(col, n) == [1, 3]


def test_disconnected_node_is_never_sensitive():
    # A disconnected node (node 2) must never change any column.
    n = 3
    C = [[0, 1, 0], [1, 0, 0], [0, 0, 0]]  # node 2 feeds nobody, receives nobody
    net = Network(n=n, C=C, gates=["OR", "OR", "FALSE"])
    for k in range(n):
        col = node_output_column(net, k)
        assert 2 not in essential_variables(col, n)


# ---------------------------------------------------------------------------
# Gate identification
# ---------------------------------------------------------------------------

def test_identify_symmetric_gates():
    for g in ("AND", "OR", "XOR", "NAND", "NOR", "XNOR"):
        tt = truth_table(g, 3)
        matches, canonical = identify_gate(tt)
        assert any(m.gate == g for m in matches), (g, [m.gate for m in matches])


def test_identify_kofn():
    tt = truth_table("KOFN", 4, {"k": 3})
    matches, canonical = identify_gate(tt)
    assert any(m.gate == "KOFN" and m.params.get("k") == 3 for m in matches)


def test_single_input_ambiguity_class():
    # Arity-1 identity: AND == OR == KOFN(1) == MAJORITY, all reproduce it.
    tt = [0, 1]
    matches, canonical = identify_gate(tt)
    names = {m.gate for m in matches}
    assert {"AND", "OR"} <= names


# ---------------------------------------------------------------------------
# End-to-end exact recovery over many random networks
# ---------------------------------------------------------------------------

def test_exact_recovery_random_symmetric():
    for seed in range(30):
        net = random_network(n=7, seed=seed, gate_pool="symmetric")
        rep = repertoire(net)
        _, reports = deconvolve(rep)
        result = verify(rep, reports)
        assert result["exact"], (seed, result)


def test_exact_recovery_random_full():
    for seed in range(30):
        net = random_network(n=8, seed=1000 + seed, gate_pool="all")
        rep = repertoire(net)
        _, reports = deconvolve(rep)
        result = verify(rep, reports)
        assert result["exact"], (seed, result)


def test_ca_deconvolution_exact_global_map():
    import random
    from ca_deconvolution import evolve_eca, deconvolve_ca, verify_ca
    # Named-gate rules and a chaotic rule; all must recover the exact global map.
    for rule in (254, 90, 232, 150, 30, 110):
        rng = random.Random(rule)
        diagrams = [
            evolve_eca(rule, [rng.randint(0, 1) for _ in range(12)], 10)
            for _ in range(80)
        ]
        net, reports = deconvolve_ca(diagrams, max_radius=3)
        vr = verify_ca(diagrams, net, rule=rule)
        assert vr["trajectory_exact"], rule
        assert vr["global_map_exact"], rule


def test_ca_named_gate_identities():
    import random
    from ca_deconvolution import evolve_eca, deconvolve_ca
    expected = {254: "OR", 90: "XOR", 232: "MAJORITY", 150: "XOR"}
    for rule, gate in expected.items():
        rng = random.Random(rule)
        diagrams = [
            evolve_eca(rule, [rng.randint(0, 1) for _ in range(12)], 10)
            for _ in range(80)
        ]
        _, reports = deconvolve_ca(diagrams, max_radius=3)
        interior = reports[6]
        assert interior.canonical.gate == gate, (rule, interior.canonical.gate)
    # Rule 90 drops the irrelevant centre cell.
    rng = random.Random(90)
    diagrams = [evolve_eca(90, [rng.randint(0, 1) for _ in range(12)], 10) for _ in range(80)]
    _, reports = deconvolve_ca(diagrams, max_radius=3)
    assert len(reports[6].support) == 2


def test_regulatory_gate_identity_and_forward():
    from causalbool import truth_table, apply_gate
    # a AND NOT b AND c over three inputs: single satisfying assignment a=1,b=0,c=1.
    tt = truth_table("REGULATORY", 3, {"activators": [0, 2]})
    assert sum(tt) == 1
    assert tt[0b101] == 1  # a=1 (bit0), b=0 (bit1), c=1 (bit2)
    matches, canonical = identify_gate(tt)
    assert canonical.gate == "REGULATORY"
    assert canonical.params["activators"] == [0, 2]
    # forward application matches the definition
    assert apply_gate("REGULATORY", [1, 0, 1], {"activators": [0, 2]}) == 1
    assert apply_gate("REGULATORY", [1, 1, 1], {"activators": [0, 2]}) == 0


def test_regulatory_special_cases_named_classically():
    from causalbool import truth_table
    # all activators -> AND wins by priority; all inhibitors -> NOR wins.
    tt_and = truth_table("REGULATORY", 3, {"activators": [0, 1, 2]})
    _, can_and = identify_gate(tt_and)
    assert can_and.gate == "AND"
    tt_nor = truth_table("REGULATORY", 3, {"activators": []})
    _, can_nor = identify_gate(tt_nor)
    assert can_nor.gate == "NOR"


def test_biological_networks_exact_recovery():
    import os
    from bnet import parse_bnet
    from causalbool import repertoire
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    bnet_dir = os.path.join(root, "data", "bio", "raw")
    for fname in ("pyboolnet_davidich_yeast.bnet", "pyboolnet_irma.bnet",
                  "pyboolnet_xiao_wnt5a.bnet"):
        path = os.path.join(bnet_dir, fname)
        if not os.path.exists(path):
            continue
        net, _ = parse_bnet(path)
        rep = repertoire(net)
        _, reports = deconvolve(rep)
        assert verify(rep, reports)["exact"], fname


def test_finance_analyser_detects_determinism():
    import random
    from finance import analyse
    from ca_deconvolution import evolve_eca
    # Real deterministic system: rule-110 CA trajectory must read as exact.
    rng = random.Random(110)
    rows = evolve_eca(110, [rng.randint(0, 1) for _ in range(9)], 400)
    res = analyse(rows, max_k=3)
    assert res["mean_contradiction_rate"] == 0.0
    assert res["exact_nodes"] == res["n_nodes"]
    assert res["mean_best_accuracy"] >= 0.999


def test_finance_analyser_flags_randomness():
    import random
    from finance import analyse
    rng = random.Random(0)
    rows = [[rng.randint(0, 1) for _ in range(9)] for _ in range(400)]
    res = analyse(rows, max_k=2)
    # An independent random sequence admits no exact small-support law and
    # contradicts itself on recurring patterns.
    assert res["exact_nodes"] == 0
    assert res["mean_contradiction_rate"] > 0.2


def test_connectivity_recovered_exactly():
    # The connected set of each node must be recovered exactly (non-degenerate).
    net = random_network(n=8, seed=7, gate_pool="symmetric")
    rep = repertoire(net)
    _, reports = deconvolve(rep)
    for k in range(net.n):
        recovered = reports[k].connected_inputs
        original = net.connected_inputs(k)
        # Degenerate gates can drop an input; symmetric non-constant gates keep all.
        assert recovered == original, (k, original, recovered)
