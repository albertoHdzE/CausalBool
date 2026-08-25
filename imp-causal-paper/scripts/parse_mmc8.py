"""Parse mmc8.csv — exhaustive 5-node Boolean network dynamics data.

The paper's supplementary Data S7 (mmc8.csv) contains 9364 rows of exhaustive
BDM perturbation analysis on directed 5-node graphs.  Each row has:
  - A directed edge list in Mathematica notation
  - Per-node BDM perturbation deltas (C(G) - C(G\\v))

This corresponds to Figure 4D in the paper.

Usage:
    .venv/bin/python scripts/parse_mmc8.py
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "zenil_supplementary" / "mmc8.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "boolean_exhaustive"


def parse_mathematica_edge_list(s: str) -> list[tuple[int, int]]:
    """Parse '{{0, 4}, {1, 4}, ...}' into a list of (source, target) tuples."""
    pairs = re.findall(r"\{(\d+),\s*(\d+)\}", s)
    return [(int(a), int(b)) for a, b in pairs]


def parse_mathematica_perturbation(s: str) -> dict[int, float]:
    """Parse '{{4, 3.748}, {3, 0.}, ...}' into {node: delta} dict."""
    pairs = re.findall(r"\{(\d+),\s*(-?[\d.eE+-]+)\}", s)
    return {int(node): float(val) for node, val in pairs}


def classify_delta(delta: float, threshold: float) -> str:
    if delta > threshold:
        return "positive"
    if delta < -threshold:
        return "negative"
    return "neutral"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    with open(INPUT_FILE) as f:
        reader = csv.reader(f)
        for row in reader:
            idx = int(row[0])
            edges = parse_mathematica_edge_list(row[1])
            deltas = parse_mathematica_perturbation(row[2])
            rows.append({
                "graph_id": idx,
                "edge_list": edges,
                "num_edges": len(edges),
                "node_deltas": deltas,
            })

    print(f"Parsed {len(rows)} graphs from mmc8.csv")

    # Basic statistics
    edge_counts = [r["num_edges"] for r in rows]
    print(f"Edge count range: {min(edge_counts)}–{max(edge_counts)}")
    print(f"Edge count distribution:")
    ec_series = pd.Series(edge_counts)
    for ec, count in sorted(ec_series.value_counts().items()):
        print(f"  {ec:>2} edges: {count:>5} graphs")

    # Build a flat DataFrame with per-node deltas
    flat_rows = []
    for r in rows:
        n_edges = r["num_edges"]
        # threshold = log2(5) for 5-node graphs
        threshold = np.log2(5)
        for node, delta in r["node_deltas"].items():
            flat_rows.append({
                "graph_id": r["graph_id"],
                "num_edges": n_edges,
                "node": node,
                "delta": delta,
                "classification": classify_delta(delta, threshold),
            })

    df = pd.DataFrame(flat_rows)
    df.to_csv(OUTPUT_DIR / "mmc8_node_deltas.csv", index=False)

    # Per-graph summary
    graph_summaries = []
    for r in rows:
        deltas = list(r["node_deltas"].values())
        threshold = np.log2(5)
        n_pos = sum(1 for d in deltas if d > threshold)
        n_neg = sum(1 for d in deltas if d < -threshold)
        n_neu = 5 - n_pos - n_neg
        graph_summaries.append({
            "graph_id": r["graph_id"],
            "num_edges": r["num_edges"],
            "positive_count": n_pos,
            "neutral_count": n_neu,
            "negative_count": n_neg,
            "max_delta": max(deltas),
            "min_delta": min(deltas),
            "mean_delta": np.mean(deltas),
        })

    gdf = pd.DataFrame(graph_summaries)
    gdf.to_csv(OUTPUT_DIR / "mmc8_graph_summaries.csv", index=False)

    # Aggregate statistics for the paper
    print(f"\n--- Per-node delta statistics ---")
    print(f"Total node-delta entries: {len(df)}")
    print(f"  Positive: {(df['classification'] == 'positive').sum()}")
    print(f"  Neutral:  {(df['classification'] == 'neutral').sum()}")
    print(f"  Negative: {(df['classification'] == 'negative').sum()}")
    print(f"  Delta range: [{df['delta'].min():.4f}, {df['delta'].max():.4f}]")
    print(f"  Mean delta: {df['delta'].mean():.4f}")

    # Distribution by edge count (key for Figure 4D)
    print(f"\n--- Classification by edge count (Figure 4D) ---")
    pivot = df.groupby(["num_edges", "classification"]).size().unstack(fill_value=0)
    for col in ["positive", "neutral", "negative"]:
        if col not in pivot.columns:
            pivot[col] = 0
    pivot = pivot[["positive", "neutral", "negative"]]
    pivot["total_nodes"] = pivot.sum(axis=1)
    pivot["pct_positive"] = (pivot["positive"] / pivot["total_nodes"] * 100).round(1)
    pivot["pct_negative"] = (pivot["negative"] / pivot["total_nodes"] * 100).round(1)
    print(pivot.to_string())

    pivot.to_csv(OUTPUT_DIR / "mmc8_classification_by_edges.csv")

    # Save edge lists for potential graph reconstruction
    edge_list_records = []
    for r in rows:
        edge_list_records.append({
            "graph_id": r["graph_id"],
            "num_edges": r["num_edges"],
            "edges": str(r["edge_list"]),
        })
    eldf = pd.DataFrame(edge_list_records)
    eldf.to_csv(OUTPUT_DIR / "mmc8_edge_lists.csv", index=False)

    # Summary JSON
    summary = {
        "source": "mmc8.csv (iScience 2019 Data S7)",
        "description": "Exhaustive BDM node perturbation on 5-node directed graphs",
        "total_graphs": len(rows),
        "nodes_per_graph": 5,
        "threshold": float(np.log2(5)),
        "edge_count_range": [min(edge_counts), max(edge_counts)],
        "total_node_deltas": len(df),
        "classification_counts": {
            "positive": int((df["classification"] == "positive").sum()),
            "neutral": int((df["classification"] == "neutral").sum()),
            "negative": int((df["classification"] == "negative").sum()),
        },
        "delta_range": [float(df["delta"].min()), float(df["delta"].max())],
    }
    with open(OUTPUT_DIR / "mmc8_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nOutputs saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
