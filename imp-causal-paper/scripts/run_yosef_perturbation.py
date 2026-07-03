"""Run BDM node perturbation on all three Yosef time-window networks.

Outputs per-network CSVs and a summary JSON to data/processed/th17/yosef_perturbation/.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from imp_causal_paper.complexity import BDMComplexityEstimator
from imp_causal_paper.perturbation import GraphPerturbationAnalyzer
from imp_causal_paper.yosef_network import parse_yosef_networks

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "processed" / "th17" / "yosef_perturbation"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    networks = parse_yosef_networks()
    estimator = BDMComplexityEstimator()
    analyzer = GraphPerturbationAnalyzer(estimator)

    summary: dict[str, object] = {}

    for zenil_name in ["EarlyNet", "IntermediateNet", "FinalNet"]:
        net = networks[zenil_name]
        G = net.graph
        print(f"\n{'='*60}")
        print(f"Processing {zenil_name} ({net.node_count} nodes, {net.edge_count} edges)")
        print(f"{'='*60}")

        t0 = time.time()
        spectra = analyzer.spectra(G, what="vertices")
        elapsed = time.time() - t0
        print(f"  Completed in {elapsed:.1f}s")

        # Save full spectra
        spectra_path = OUTPUT_DIR / f"{zenil_name}_node_spectra.csv"
        spectra.to_csv(spectra_path, index=False)
        print(f"  Saved: {spectra_path.name}")

        # Signature (sorted)
        signature = spectra.sort_values(
            by=["delta", "source"], ascending=[False, True]
        ).reset_index(drop=True)
        sig_path = OUTPUT_DIR / f"{zenil_name}_node_signature.csv"
        signature.to_csv(sig_path, index=False)

        # Classification counts
        neg = spectra[spectra["classification"] == "negative"]
        pos = spectra[spectra["classification"] == "positive"]
        neu = spectra[spectra["classification"] == "neutral"]

        neg_nodes = sorted(neg["element"].tolist())
        pos_nodes = sorted(pos["element"].tolist())

        print(f"  Positive: {len(pos)}, Neutral: {len(neu)}, Negative: {len(neg)}")
        if neg_nodes:
            print(f"  Negative nodes: {neg_nodes}")

        # Reprogrammability
        deltas = spectra["delta"].to_numpy(dtype=float)
        mad = float(np.median(np.abs(deltas - np.median(deltas))))
        max_abs = float(np.max(np.abs(deltas)))
        rel_reprog = mad / max_abs if max_abs != 0 else 0.0

        summary[zenil_name] = {
            "yosef_sheet": net.yosef_sheet,
            "node_count": net.node_count,
            "edge_count": net.edge_count,
            "tf_count": net.tf_count,
            "target_count": net.target_count,
            "base_complexity": float(spectra["base_complexity"].iloc[0]),
            "positive_count": len(pos),
            "neutral_count": len(neu),
            "negative_count": len(neg),
            "negative_nodes": neg_nodes,
            "positive_nodes": pos_nodes[:20],  # truncate for readability
            "relative_reprogrammability": rel_reprog,
            "elapsed_seconds": round(elapsed, 1),
        }

    # Save summary
    summary_path = OUTPUT_DIR / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved: {summary_path}")

    # Verification: check Zenil's claim about FinalNet
    final_neg = summary["FinalNet"]["negative_nodes"]
    zenil_claim = {"STAT6", "TCFEB", "TRIM24"}
    print(f"\n{'='*60}")
    print("VERIFICATION: Zenil claims only STAT6, TCFEB, TRIM24 are negative in FinalNet")
    print(f"  Our negative nodes: {final_neg}")
    if set(final_neg) == zenil_claim:
        print("  MATCH: exact agreement with paper")
    else:
        print(f"  MISMATCH: paper claims {sorted(zenil_claim)}, we found {final_neg}")
        overlap = set(final_neg) & zenil_claim
        extra = set(final_neg) - zenil_claim
        missing = zenil_claim - set(final_neg)
        if overlap:
            print(f"  Overlap: {sorted(overlap)}")
        if extra:
            print(f"  Extra (we found, paper didn't): {sorted(extra)}")
        if missing:
            print(f"  Missing (paper found, we didn't): {sorted(missing)}")


if __name__ == "__main__":
    main()
