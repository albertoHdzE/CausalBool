"""Tests for Yosef et al. 2013 network parsing and BDM perturbation."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest
import networkx as nx

from imp_causal_paper.yosef_network import parse_yosef_networks, DEFAULT_XLS

GROUND_TRUTH_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "zenil_supplementary"

pytestmark = pytest.mark.skipif(
    not DEFAULT_XLS.exists(),
    reason="Yosef Table S3 XLS not downloaded",
)


@pytest.fixture(scope="module")
def networks():
    return parse_yosef_networks()


def test_three_networks_parsed(networks):
    assert set(networks.keys()) == {"EarlyNet", "IntermediateNet", "FinalNet"}


def test_early_network_dimensions(networks):
    net = networks["EarlyNet"]
    assert net.yosef_sheet == "Early"
    assert net.edge_count == 4218
    assert net.tf_count == 53
    assert net.node_count == 578


def test_intermediate_network_dimensions(networks):
    net = networks["IntermediateNet"]
    assert net.yosef_sheet == "Intermediate"
    assert net.edge_count == 7204
    assert net.tf_count == 60
    assert net.node_count == 1027


def test_finalnet_dimensions(networks):
    net = networks["FinalNet"]
    assert net.yosef_sheet == "Late"
    assert net.edge_count == 6894
    assert net.tf_count == 50
    assert net.node_count == 1107


def test_all_graphs_are_directed(networks):
    for name, net in networks.items():
        assert isinstance(net.graph, nx.DiGraph), f"{name} should be DiGraph"


def test_key_tfs_present_in_finalnet(networks):
    """STAT6, TCFEB, TRIM24 must be nodes in FinalNet (the Zenil paper's candidates)."""
    G = networks["FinalNet"].graph
    for tf in ["STAT6", "TCFEB", "TRIM24"]:
        assert tf in G.nodes(), f"{tf} missing from FinalNet"


def test_key_tfs_are_regulators_in_finalnet(networks):
    """All three must have outgoing edges (they are TFs, not mere targets)."""
    G = networks["FinalNet"].graph
    for tf in ["STAT6", "TCFEB", "TRIM24"]:
        assert G.out_degree(tf) > 0, f"{tf} has no outgoing edges in FinalNet"


def test_ground_truth_finalnet_negative_genes_are_exactly_three():
    """The Zenil paper's ground truth (mmc6.csv) lists exactly STAT6, TCFEB, TRIM24."""
    gt_path = GROUND_TRUTH_DIR / "mmc6.csv"
    if not gt_path.exists():
        pytest.skip("Zenil supplementary mmc6.csv not available")
    genes = []
    with open(gt_path) as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) >= 2:
                genes.append(parts[0])
    assert set(genes) == {"STAT6", "TCFEB", "TRIM24"}


def test_ground_truth_gene_counts_match_paper():
    """Verify that the supplementary CSVs have the expected gene counts per time window."""
    expected = {
        "mmc2.csv": 223,  # EarlyNet negative
        "mmc3.csv": 15,   # EarlyNet positive
        "mmc4.csv": 360,  # IntermediateNet negative
        "mmc5.csv": 3,    # IntermediateNet positive
        "mmc6.csv": 3,    # FinalNet negative
        "mmc7.csv": 239,  # FinalNet positive
    }
    for fname, exp_count in expected.items():
        path = GROUND_TRUTH_DIR / fname
        if not path.exists():
            pytest.skip(f"Zenil supplementary {fname} not available")
        count = 0
        with open(path) as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    count += 1
        assert count == exp_count, f"{fname}: expected {exp_count}, got {count}"
