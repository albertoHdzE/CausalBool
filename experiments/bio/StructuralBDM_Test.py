
import json
import numpy as np
from pathlib import Path
from pybdm import BDM
from typing import List, Tuple

def load_network(name: str) -> np.ndarray:
    """Load a network's adjacency matrix from processed JSON."""
    base_path = Path("data/bio/processed")
    file_path = base_path / f"{name}.json"
    with open(file_path, "r") as f:
        data = json.load(f)
    return np.array(data["cm"], dtype=int)

def randomize_matrix(cm: np.ndarray, swaps: int = 1000) -> np.ndarray:
    """
    Randomize a directed adjacency matrix while preserving in/out degrees
    using the Maslov-Sneppen algorithm (edge swapping).
    """
    cm_rand = cm.copy()
    rows, cols = np.nonzero(cm_rand)
    edges = list(zip(rows, cols))
    n_edges = len(edges)
    
    if n_edges < 2:
        return cm_rand
        
    for _ in range(swaps):
        # Pick two edges at random: (u, v) and (x, y)
        idx1, idx2 = np.random.choice(n_edges, 2, replace=False)
        u, v = edges[idx1]
        x, y = edges[idx2]
        
        # Try to swap targets: (u, y) and (x, v)
        # Check 1: Avoid self-loops (u==y or x==v)
        if u == y or x == v:
            continue
            
        # Check 2: Avoid duplicate edges (if u->y or x->v already exists)
        if cm_rand[u, y] == 1 or cm_rand[x, v] == 1:
            continue
            
        # Perform swap
        cm_rand[u, v] = 0
        cm_rand[x, y] = 0
        cm_rand[u, y] = 1
        cm_rand[x, v] = 1
        
        # Update edge list
        edges[idx1] = (u, y)
        edges[idx2] = (x, v)
        
    return cm_rand

def compute_structural_bdm():
    """
    Compute Structural BDM for biological networks vs randomized controls.
    """
    networks = ["lambda_phage", "lac_operon", "yeast_cell_cycle", "tcell_activation"]
    # BDM(ndim=1) for flattened array
    bdm = BDM(ndim=1)
    
    print(f"{'Network':<20} | {'Nodes':<5} | {'BDM(Bio)':<10} | {'BDM(Rand)':<10} | {'Ratio':<6} | {'Z-Score':<8}")
    print("-" * 75)
    
    results = {}
    
    for name in networks:
        # 1. Load Bio Network
        cm_bio_raw = load_network(name)
        n = cm_bio_raw.shape[0]
        
        # Sort nodes by degree
        degrees = cm_bio_raw.sum(axis=0) + cm_bio_raw.sum(axis=1)
        idx = np.argsort(degrees)[::-1]
        cm_bio = cm_bio_raw[idx][:, idx]
        
        # Flatten for 1D BDM
        flat_bio = cm_bio.flatten()
        
        # 2. Compute Bio BDM
        bdm_bio = bdm.bdm(flat_bio)
        
        # 3. Generate Random Ensemble
        rand_bdms = []
        n_swaps = n * 20
        for _ in range(100): 
            cm_rand_raw = randomize_matrix(cm_bio_raw, swaps=n_swaps)
            
            # Sort and flatten
            degrees_rand = cm_rand_raw.sum(axis=0) + cm_rand_raw.sum(axis=1)
            idx_rand = np.argsort(degrees_rand)[::-1]
            cm_rand = cm_rand_raw[idx_rand][:, idx_rand]
            
            rand_bdms.append(bdm.bdm(cm_rand.flatten()))
            
        mean_rand = np.mean(rand_bdms)
        std_rand = np.std(rand_bdms)
        
        # 4. Stats
        ratio = bdm_bio / mean_rand
        z_score = (bdm_bio - mean_rand) / std_rand if std_rand > 0 else 0.0
        
        print(f"{name:<20} | {n:<5} | {bdm_bio:<10.2f} | {mean_rand:<10.2f} | {ratio:<6.3f} | {z_score:<8.2f}")
        
        results[name] = {
            "bdm_bio": bdm_bio,
            "bdm_rand_mean": mean_rand,
            "z_score": z_score
        }
        
    return results

if __name__ == "__main__":
    np.random.seed(42)
    compute_structural_bdm()
