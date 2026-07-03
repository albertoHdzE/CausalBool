"""Parse RegulonDB NetworkRegulatorGene.txt into a NetworkX directed graph.

The Zenil 2019 paper used "a highly curated E. coli transcriptional network
(only experimentally validated connections) from the RegulonDB". This script
parses the downloaded NetworkRegulatorGene.txt (RegulonDB 14.5, 2026-07-03)
at the Confirmed (C) confidence level, which best matches that description.

The exact RegulonDB version used in the paper (~9.x, 2018) is not recoverable
as a static file; version 14.5 is used here with appropriate documentation.

Usage:
    .venv/bin/python scripts/parse_ecoli_network.py [--confidence C|CS|all]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import networkx as nx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = PROJECT_ROOT / "data" / "raw" / "regulondb" / "NetworkRegulatorGene.txt"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "ecoli"


def parse_network(confidence: str = "C") -> nx.DiGraph:
    """Parse NetworkRegulatorGene.txt and return a directed TF->gene graph.

    Args:
        confidence: One of 'C' (Confirmed only), 'CS' (Confirmed + Strong),
                    or 'all' (all interactions).
    """
    allowed = {"C"} if confidence == "C" else {"C", "S"} if confidence == "CS" else None
    lines = RAW_FILE.read_text(encoding="utf-8").splitlines()

    G: nx.DiGraph = nx.DiGraph()
    for line in lines:
        if not line or line.startswith("1)") or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        tf_name = parts[1].strip()
        gene_name = parts[4].strip()
        func = parts[5].strip()
        conf = parts[6].strip()
        if not tf_name or not gene_name:
            continue
        if allowed is not None and conf not in allowed:
            continue
        G.add_edge(tf_name, gene_name, function=func, confidence=conf)

    return G


def main(confidence: str = "C") -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    G = parse_network(confidence)
    tfs = {n for n in G.nodes() if G.out_degree(n) > 0 and G.in_degree(n) == 0
           or G.out_degree(n) > 0}
    targets = set(G.nodes()) - tfs

    print(f"RegulonDB E. coli TF->gene network (confidence={confidence})")
    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Edges: {G.number_of_edges()}")

    # Count TFs (nodes with outgoing edges) vs pure targets
    pure_tfs = {n for n in G.nodes() if G.out_degree(n) > 0}
    pure_targets = {n for n in G.nodes() if G.out_degree(n) == 0}
    print(f"  TFs (out-degree > 0): {len(pure_tfs)}")
    print(f"  Pure targets (out-degree = 0): {len(pure_targets)}")

    # Save adjacency list
    adj_path = OUTPUT_DIR / f"ecoli_tf_gene_conf{confidence}.txt"
    with open(adj_path, "w") as f:
        f.write("# RegulonDB 14.5 E. coli TF->gene network\n")
        f.write(f"# Confidence filter: {confidence}\n")
        f.write(f"# Downloaded: 2026-07-03\n")
        f.write("# Columns: tf_name\tgene_name\tfunction\tconfidence\n")
        for u, v, d in sorted(G.edges(data=True)):
            f.write(f"{u}\t{v}\t{d.get('function','')}\t{d.get('confidence','')}\n")
    print(f"  Saved: {adj_path.name}")

    # Save summary
    summary = {
        "source": "RegulonDB",
        "version": "14.5",
        "download_date": "2026-07-03",
        "confidence_filter": confidence,
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "tf_count": len(pure_tfs),
        "pure_target_count": len(pure_targets),
        "note": (
            "RegulonDB 14.5 (2026). Paper used ~RegulonDB 9.x (2018). "
            "Confidence='C' (Confirmed) best matches 'experimentally validated' description."
        ),
    }
    summary_path = OUTPUT_DIR / f"ecoli_network_conf{confidence}_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  Saved: {summary_path.name}")

    return G


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--confidence", default="C", choices=["C", "CS", "all"],
                        help="Confidence filter (default: C = Confirmed only)")
    args = parser.parse_args()
    main(args.confidence)
