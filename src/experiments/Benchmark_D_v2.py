#!/usr/bin/env python3
"""
Benchmark_D_v2.py
-----------------
Phase 1 Benchmark: Integration & Validation of Universal D_v2 Metric.
Replicates Level 2 results (Simplicity & Universality) on N=10 biological networks.

Usage:
    python Benchmark_D_v2.py

Output:
    results/lev3/benchmark_dv2.json
    Console summary table.
"""

import json
import numpy as np
import os
import sys
import copy
from pathlib import Path

# Add src to path
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

from integration.Universal_D_v2_Encoder import UniversalDv2Encoder

def degree_preserving_randomization(adj, swaps=10):
    """
    Randomize matrix while preserving in/out degrees (Maslov-Sneppen).
    """
    adj = np.array(adj, dtype=int)
    rows, cols = adj.shape
    if rows != cols:
        raise ValueError("Adjacency matrix must be square.")
    
    # Get edges
    edges = np.argwhere(adj > 0).tolist()
    n_edges = len(edges)
    if n_edges < 2:
        return adj
        
    for _ in range(swaps * n_edges):
        # Pick two random edges
        i = np.random.randint(n_edges)
        j = np.random.randint(n_edges)
        if i == j: continue
        
        u, v = edges[i]
        x, y = edges[j]
        
        # Avoid self-loops and existing edges for swap (u->y, x->v)
        if u == y or x == v: continue
        if adj[u, y] == 1 or adj[x, v] == 1: continue
        
        # Swap
        adj[u, v] = 0
        adj[x, y] = 0
        adj[u, y] = 1
        adj[x, v] = 1
        
        edges[i] = [u, y]
        edges[j] = [x, v]
        
    return adj

def simple_randomization(adj):
    """Erdos-Renyi with same density."""
    adj = np.array(adj)
    n = adj.shape[0]
    density = np.sum(adj) / (n * n)
    return (np.random.random((n, n)) < density).astype(int)

def main():
    base_dir = Path(__file__).resolve().parent.parent.parent
    data_dir = base_dir / "data" / "bio" / "processed"
    out_dir = base_dir / "results" / "lev3"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    print(f"{'Network':<25} | {'N':<3} | {'D_v2 (Bio)':<10} | {'D_v2 (Rand)':<10} | {'Z-Score':<8}")
    print("-" * 75)
    
    for json_file in sorted(data_dir.glob("*.json")):
        if json_file.name == "truth_tables.json" or json_file.name == "gate_histogram.json":
            continue
            
        with open(json_file) as f:
            data = json.load(f)
            
        if "cm" not in data:
            continue
            
        name = data.get("name", json_file.stem)
        adj = np.array(data["cm"])
        n = adj.shape[0]
        
        # 1. Compute Bio D_v2
        encoder = UniversalDv2Encoder(adj)
        d_bio = encoder.compute()["dv2"]
        
        # 2. Null Model (Degree Preserving)
        # We use degree preserving as it's a stronger null model for biological claims
        n_rand = 10
        d_rands = []
        
        for _ in range(n_rand):
            # Use copy of adj to avoid modifying original
            # Note: degree_preserving_randomization modifies in place? No, it takes array.
            # But wait, python passes by reference.
            # Let's ensure we copy.
            rand_adj = degree_preserving_randomization(adj.copy(), swaps=10)
            enc_rand = UniversalDv2Encoder(rand_adj)
            d_rands.append(enc_rand.compute()["dv2"])
            
        mean_rand = np.mean(d_rands)
        std_rand = np.std(d_rands)
        
        if std_rand == 0:
            z_score = 0
        else:
            z_score = (d_bio - mean_rand) / std_rand
            
        print(f"{name:<25} | {n:<3} | {d_bio:10.2f} | {mean_rand:10.2f} | {z_score:8.2f}")
        
        results.append({
            "name": name,
            "n": int(n),
            "d_bio": float(d_bio),
            "d_rand_mean": float(mean_rand),
            "d_rand_std": float(std_rand),
            "z_score": float(z_score)
        })
        
    # Save results
    with open(out_dir / "benchmark_dv2.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"\nResults saved to {out_dir / 'benchmark_dv2.json'}")

if __name__ == "__main__":
    main()
