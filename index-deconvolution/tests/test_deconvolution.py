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
