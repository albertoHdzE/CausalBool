"""Run BDM node perturbation on the RegulonDB E. coli TF->gene network.

Reproduces the Zenil 2019 E. coli analysis: computes BDM perturbation
spectra for each node and classifies nodes as positive, neutral, or negative.

The paper used RegulonDB ~9.x (2018); this script uses the downloaded
RegulonDB 14.5 (2026-07-03) at Confirmed (C) confidence level.

Node ordering: alphabetical (sorted). No ordering discrepancy has been
identified for this network; the default is used unless evidence suggests
otherwise.

Usage:
    .venv/bin/python scripts/run_ecoli_perturbation.py [--confidence C|CS|all]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from imp_causal_paper.complexity import BDMComplexityEstimator
from imp_causal_paper.perturbation import GraphPerturbationAnalyzer

# Allow importing sibling script without installing the scripts/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_ecoli_network import parse_network  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "processed" / "ecoli"


def main(confidence: str = "C") -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    G = parse_network(confidence)
    print(f"\nE. coli TF->gene network (confidence={confidence})")
    print(f"  Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")

    estimator = BDMComplexityEstimator()
    analyzer = GraphPerturbationAnalyzer(estimator)

    print(f"\nRunning BDM node perturbation (alphabetical node ordering)...")
    t0 = time.time()
    spectra = analyzer.spectra(G, what="vertices")
    elapsed = time.time() - t0
    print(f"  Completed in {elapsed:.1f}s")

    # Save spectra
    spectra_path = OUTPUT_DIR / f"ecoli_conf{confidence}_node_spectra.csv"
    spectra.to_csv(spectra_path, index=False)
    print(f"  Saved: {spectra_path.name}")

    # Signature (sorted by delta)
    signature = spectra.sort_values(by=["delta", "source"], ascending=[False, True]).reset_index(drop=True)
    sig_path = OUTPUT_DIR / f"ecoli_conf{confidence}_node_signature.csv"
    signature.to_csv(sig_path, index=False)
    print(f"  Saved: {sig_path.name}")

    # Classification summary
    neg = spectra[spectra["classification"] == "negative"]
    pos = spectra[spectra["classification"] == "positive"]
    neu = spectra[spectra["classification"] == "neutral"]
    neg_nodes = sorted(neg["element"].tolist())
    pos_nodes = sorted(pos["element"].tolist())

    print(f"\n  Positive: {len(pos)}, Neutral: {len(neu)}, Negative: {len(neg)}")
    if neg_nodes:
        print(f"  Negative nodes: {neg_nodes}")
    if pos_nodes:
        print(f"  Top positive nodes: {pos_nodes[:10]}")

    # Reprogrammability
    deltas = spectra["delta"].to_numpy(dtype=float)
    mad = float(np.median(np.abs(deltas - np.median(deltas))))
    max_abs = float(np.max(np.abs(deltas))) if len(deltas) else 0.0
    rel_reprog = mad / max_abs if max_abs != 0 else 0.0

    summary = {
        "source": "RegulonDB",
        "version": "14.5",
        "download_date": "2026-07-03",
        "confidence_filter": confidence,
        "node_ordering": "sorted",
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "base_complexity": float(spectra["base_complexity"].iloc[0]),
        "positive_count": len(pos),
        "neutral_count": len(neu),
        "negative_count": len(neg),
        "negative_nodes": neg_nodes,
        "positive_nodes": pos_nodes[:20],
        "relative_reprogrammability": rel_reprog,
        "elapsed_seconds": round(elapsed, 1),
        "note": (
            "Paper used RegulonDB ~9.x (2018). Version 14.5 (2026) used here; "
            "network size differs. No ground truth BDM values available for direct comparison."
        ),
    }

    summary_path = OUTPUT_DIR / f"ecoli_conf{confidence}_perturbation_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Saved: {summary_path.name}")
    print(f"  Relative reprogrammability: {rel_reprog:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--confidence", default="C", choices=["C", "CS", "all"],
                        help="Confidence filter (default: C = Confirmed only)")
    args = parser.parse_args()
    main(args.confidence)
