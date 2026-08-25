#!/usr/bin/env python3
"""
run_ecoli_enrichment.py

Run GO/KEGG enrichment on E. coli positive and negative gene sets from BDM
perturbation analysis. Reproduces Fig 5A.

Uses STRING API enrichment endpoint (supports E. coli K-12).
g:Profiler does not support E. coli.
"""
import os
import sys
import json
import urllib.request
import urllib.parse

import pandas as pd

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
processed_dir = os.path.join(project_root, "data", "processed", "ecoli")

spectra = pd.read_csv(os.path.join(processed_dir, "ecoli_confC_node_spectra.csv"))

positive_genes = spectra[spectra["classification"] == "positive"]["element"].tolist()
negative_genes = spectra[spectra["classification"] == "negative"]["element"].tolist()
neutral_genes = spectra[spectra["classification"] == "neutral"]["element"].tolist()

print(f"Positive: {len(positive_genes)}, Negative: {len(negative_genes)}, Neutral: {len(neutral_genes)}")

STRING_API = "https://string-db.org/api"
SPECIES = 511145  # E. coli K-12 MG1655


def string_enrichment(genes, label):
    """Query STRING enrichment API for a gene list."""
    url = f"{STRING_API}/json/enrichment"
    params = urllib.parse.urlencode({
        "identifiers": "%0d".join(genes),
        "species": SPECIES,
        "caller_identity": "imp_causal_paper_reproduction",
    })
    req = urllib.request.Request(url, data=params.encode())
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  STRING API error for {label}: {e}")
        return pd.DataFrame()

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    return df


for label, genes in [("positive", positive_genes), ("negative", negative_genes)]:
    if not genes:
        print(f"\n{label}: no genes, skipping")
        continue

    print(f"\n{'='*60}")
    print(f"Enrichment for {label} genes ({len(genes)} genes)")
    print(f"{'='*60}")

    result = string_enrichment(genes, label)

    if result.empty:
        print("  No enrichments returned.")
        continue

    # Filter to FDR < 0.05
    result = result[result["fdr"].astype(float) < 0.05].copy()
    result = result.sort_values("fdr")

    out_file = os.path.join(processed_dir, f"ecoli_{label}_enrichment.csv")
    result.to_csv(out_file, index=False)
    print(f"  {len(result)} significant terms (FDR < 0.05)")
    print(f"  Saved to {out_file}")

    # Show top results by category
    for cat in ["Process", "KEGG", "Component", "Function"]:
        subset = result[result["category"] == cat] if "category" in result.columns else pd.DataFrame()
        if subset.empty:
            continue
        print(f"\n  {cat} (top 10):")
        for _, row in subset.head(10).iterrows():
            desc = str(row.get("description", row.get("term", "")))[:55]
            fdr = float(row["fdr"])
            n = row.get("number_of_genes", "?")
            print(f"    {desc:55s} FDR={fdr:.2e} (n={n})")
