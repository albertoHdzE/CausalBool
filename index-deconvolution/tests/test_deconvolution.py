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

def test_or_never_confused_with_and_over_exhaustive_data():
    from causalbool import truth_table
    # OR equals AND only at arity 1 (both are the identity); for arity >= 2 they
    # have different truth tables and cannot be confused over exhaustive inputs.
    assert truth_table("OR", 1) == truth_table("AND", 1)
    for m in (2, 3, 4):
        assert truth_table("OR", m) != truth_table("AND", m)


def test_reachable_state_correlation_can_hide_inputs():
    # Counterexample: node1 and node2 both copy node0, so they are always equal
    # in reachable states; OR(node1,node2) is then indistinguishable from
    # AND(node1,node2).  Exhaustive deconvolution still recovers OR of {1,2}.
    from causalbool import Network, repertoire, step, input_vector
    n = 4
    C = [[0] * n for _ in range(n)]
    C[0][0] = 1; C[1][0] = 1; C[2][0] = 1; C[3][1] = 1; C[3][2] = 1
    net = Network(n=n, C=C, gates=["NOT", "LUT", "LUT", "OR"],
                  params=[{}, {"table": [0, 1]}, {"table": [0, 1]}, {}])
    _, reports = deconvolve(repertoire(net))
    assert set(reports[3].connected_inputs) == {1, 2}
    assert reports[3].canonical.gate == "OR"
    # reachable states: node1 == node2 always -> the inputs are confounded
    reachable = {tuple(step(net, input_vector(x, n))) for x in range(2 ** n)}
    assert all(s[1] == s[2] for s in reachable)


def test_verify_forward_is_independent_and_exact():
    # The recovered network must reproduce the repertoire through the forward
    # model alone (no reports, no stored columns): a non-circular check.
    from deconvolution import verify_forward
    for seed in range(50):
        net = random_network(n=8, seed=3000 + seed, gate_pool="all")
        rep = repertoire(net)
        rnet, _ = deconvolve(rep)
        assert verify_forward(rep, rnet)["exact"], seed


def test_random_data_is_not_compressed():
    # Falsifiability: a fit-anything method would give small rules for random
    # functions.  Ours does not; random 6-input functions need many DNF clauses.
    import random
    from deconvolution import minimal_dnf
    from causalbool import truth_table
    rng = random.Random(1)
    counts = []
    for _ in range(50):
        tt = [rng.randint(0, 1) for _ in range(64)]
        if sum(tt) in (0, 64):
            continue
        counts.append(len(minimal_dnf(tt)))
    avg = sum(counts) / len(counts)
    assert avg > 8, avg                                   # random needs many clauses
    assert len(minimal_dnf(truth_table("AND", 6))) == 1   # structure needs one


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


def test_regulatory_dnf_identification_and_reproduction():
    from causalbool import truth_table
    # (a AND b) OR (a AND NOT c): a genuine two-clause regulatory function.
    def f(a, b, c):
        return int((a and b) or (a and not c))
    reduced = [f((y >> 0) & 1, (y >> 1) & 1, (y >> 2) & 1) for y in range(8)]
    matches, canonical = identify_gate(reduced)
    assert canonical.gate == "REGULATORY_DNF"
    assert truth_table("REGULATORY_DNF", 3, canonical.params) == reduced
    # every clause is a real compression: fewer clauses than on-set minterms
    assert len(canonical.params["clauses"]) < sum(reduced)


def test_regulatory_dnf_does_not_override_named_gates():
    from causalbool import truth_table
    # XOR has many minterms but a canonical name; DNF must not win.
    _, can = identify_gate(truth_table("XOR", 3))
    assert can.gate == "XOR"
    _, can2 = identify_gate(truth_table("MAJORITY", 3))
    assert can2.gate == "MAJORITY"


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


def test_reprogramming_measures():
    from causalbool import Network
    from reprogramming import image_size, num_attractors, knockout, spectrum
    n = 4
    # Identity network: each node copies itself. A bijection: image is all states,
    # every state is a fixed point.
    C = [[1 if i == k else 0 for i in range(n)] for k in range(n)]
    ident = Network(n=n, C=C, gates=["LUT"] * n,
                    params=[{"table": [0, 1]} for _ in range(n)])
    assert image_size(ident) == 2 ** n
    assert num_attractors(ident) == 2 ** n
    # Constant network: everything collapses to one state, one attractor.
    const = Network(n=n, C=[[0] * n for _ in range(n)], gates=["FALSE"] * n,
                    params=[{} for _ in range(n)])
    assert image_size(const) == 1
    assert num_attractors(const) == 1
    # Knockout fixes a node to a constant.
    ko = knockout(ident, 0)
    assert ko.gates[0] == "FALSE"
    assert len(spectrum(ident, image_size)) == n


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
