"""Re-run EarlyNet BDM node perturbation using algodyn's exact 3x3 CTM table.

Standard pybdm (4x4 blocks) produces only 7% sign agreement with the paper's
ground truth for EarlyNet.  This script uses algodyn's exact K-3x3.csv CTM
values to match the paper's BDM implementation and should produce ~97-99%
sign agreement, consistent with IntermediateNet and FinalNet.

Usage:
    .venv/bin/python scripts/run_earlynet_algodyn.py
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import numpy as np

from imp_causal_paper.algodyn_bdm import AlgodynBDMEstimator
from imp_causal_paper.perturbation import GraphPerturbationAnalyzer
from imp_causal_paper.yosef_network import parse_yosef_networks

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "th17" / "yosef_perturbation"
GT_DIR = PROJECT_ROOT / "data" / "raw" / "zenil_supplementary"


def load_ground_truth(neg_file: str, pos_file: str) -> dict[str, float]:
    """Load the paper's algodyn ground-truth deltas from supplementary CSVs."""
    vals: dict[str, float] = {}
    for fname in [neg_file, pos_file]:
        path = GT_DIR / fname
        with open(path) as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    try:
                        vals[parts[0]] = float(parts[1])
                    except ValueError:
                        continue
    return vals


def sign_agreement(our: dict[str, float], gt: dict[str, float]) -> tuple[int, int, int]:
    """Count sign agreement between our deltas and ground truth."""
    agree = disagree = 0
    common = set(our) & set(gt)
    for gene in common:
        if (our[gene] > 0 and gt[gene] > 0) or (our[gene] < 0 and gt[gene] < 0):
            agree += 1
        else:
            disagree += 1
    return agree, disagree, len(common)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    networks = parse_yosef_networks()
    estimator = AlgodynBDMEstimator(block_size=3)
    analyzer = GraphPerturbationAnalyzer(estimator)

    # Ground truth mapping: network -> (negative_file, positive_file)
    gt_mapping = {
        "EarlyNet": ("mmc2.csv", "mmc3.csv"),
        "IntermediateNet": ("mmc4.csv", "mmc5.csv"),
        "FinalNet": ("mmc6.csv", "mmc7.csv"),
    }

    # Run EarlyNet with algodyn 3x3
    net = networks["EarlyNet"]
    G = net.graph
    print(f"Processing EarlyNet ({net.node_count} nodes, {net.edge_count} edges)")
    print(f"Using algodyn CTM table (3x3 blocks)")

    t0 = time.time()
    spectra = analyzer.spectra(G, what="vertices")
    elapsed = time.time() - t0
    print(f"Completed in {elapsed:.1f}s")

    # Save results
    spectra_path = OUTPUT_DIR / "EarlyNet_algodyn3x3_node_spectra.csv"
    spectra.to_csv(spectra_path, index=False)
    print(f"Saved: {spectra_path.name}")

    signature = spectra.sort_values(
        by=["delta", "source"], ascending=[False, True]
    ).reset_index(drop=True)
    sig_path = OUTPUT_DIR / "EarlyNet_algodyn3x3_node_signature.csv"
    signature.to_csv(sig_path, index=False)

    # Cross-validate against ground truth
    gt = load_ground_truth(*gt_mapping["EarlyNet"])
    our_dict = dict(zip(spectra["element"], spectra["delta"]))
    agree, disagree, common = sign_agreement(our_dict, gt)
    pct = agree / common * 100 if common else 0

    print(f"\n{'='*60}")
    print(f"Cross-validation: algodyn 3x3 vs paper ground truth")
    print(f"  Common genes: {common}")
    print(f"  Sign agree:   {agree} ({pct:.0f}%)")
    print(f"  Sign disagree: {disagree}")
    print(f"{'='*60}")

    # Compare with pybdm 4x4 results
    pybdm_path = OUTPUT_DIR / "EarlyNet_node_spectra.csv"
    if pybdm_path.exists():
        import pandas as pd
        pybdm_df = pd.read_csv(pybdm_path)
        pybdm_dict = dict(zip(pybdm_df["element"], pybdm_df["delta"]))
        p_agree, p_disagree, p_common = sign_agreement(pybdm_dict, gt)
        p_pct = p_agree / p_common * 100 if p_common else 0
        print(f"\nComparison:")
        print(f"  pybdm 4x4:    {p_agree}/{p_common} ({p_pct:.0f}%) sign agreement")
        print(f"  algodyn 3x3:  {agree}/{common} ({pct:.0f}%) sign agreement")

    # Also cross-validate IntermediateNet and FinalNet with algodyn 3x3
    # to see if they remain high
    for name in ["IntermediateNet", "FinalNet"]:
        net2 = networks[name]
        G2 = net2.graph
        print(f"\nProcessing {name} ({net2.node_count} nodes) with algodyn 3x3...")
        t0 = time.time()
        sp2 = analyzer.spectra(G2, what="vertices")
        elapsed2 = time.time() - t0
        print(f"  Completed in {elapsed2:.1f}s")

        gt2 = load_ground_truth(*gt_mapping[name])
        our2 = dict(zip(sp2["element"], sp2["delta"]))
        a2, d2, c2 = sign_agreement(our2, gt2)
        pct2 = a2 / c2 * 100 if c2 else 0
        print(f"  algodyn 3x3: {a2}/{c2} ({pct2:.0f}%) sign agreement")

        # Save
        sp2.to_csv(OUTPUT_DIR / f"{name}_algodyn3x3_node_spectra.csv", index=False)


if __name__ == "__main__":
    main()
