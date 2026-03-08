import os
import json
import math
import random
import time
import argparse
import signal
from pathlib import Path
from typing import Dict, List, Tuple, Any
import numpy as np
import networkx as nx
import sys

# Add src to path for local imports
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))
# Local imports
from integration.Universal_D_v2_Encoder import UniversalDv2Encoder

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "bio" / "processed"
RESULTS_DIR   = Path(__file__).resolve().parents[2] / "results" / "bio"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
NULL_STATS_FILE = RESULTS_DIR / "null_stats.json"

class TimeoutException(Exception):
    pass

def signal_handler(signum, frame):
    raise TimeoutException("Time limit reached")

def load_cm(path: Path) -> Tuple[str, np.ndarray, List[str]]:
    with open(path, "r") as f:
        data = json.load(f)
    name  = data.get("name") or path.stem
    cm    = np.array(data.get("cm", []), dtype=int)
    nodes = data.get("nodes", [])
    if cm.size == 0 and nodes:
        # Fallback if edges exist (rare in processed)
        edges = data.get("edges", [])
        n     = len(nodes)
        cm    = np.zeros((n, n), dtype=int)
        idx   = {n: i for i, n in enumerate(nodes)}
        for s, t in edges:
            if s in idx and t in idx:
                cm[idx[s], idx[t]] = 1
    return name, cm, nodes

def er_edge_shuffle(cm: np.ndarray, allow_self_loops: bool = False, seed: int | None = None) -> np.ndarray:
    rng    = np.random.default_rng(seed)
    n      = cm.shape[0]
    E      = int(cm.sum())
    mask   = np.ones((n, n), dtype=bool)
    if not allow_self_loops:
        np.fill_diagonal(mask, False)
    positions = np.argwhere(mask)
    if E > len(positions):
        E = len(positions)
    chosen    = positions[rng.choice(len(positions), size=E, replace=False)]
    adj       = np.zeros_like(cm, dtype=int)
    for i, j in chosen:
        adj[i, j] = 1
    return adj

def degree_preserving_swap(cm: np.ndarray, nswap_factor: int = 10, seed: int | None = None) -> np.ndarray:
    G      = nx.from_numpy_array(cm, create_using=nx.DiGraph)
    E      = int(cm.sum())
    nswap  = max(1, nswap_factor * E)
    try:
        nx.directed_edge_swap(G, nswap=nswap, max_tries=100 * nswap, seed=seed)
    except (nx.NetworkXError, nx.NetworkXAlgorithmError):
        # Fallback: configuration model
        in_deg  = [d for _, d in G.in_degree()]
        out_deg = [d for _, d in G.out_degree()]
        try:
            G_conf = nx.directed_configuration_model(in_deg, out_deg, seed=seed)
            G      = nx.DiGraph(G_conf)  # collapse multiedges
        except Exception:
            # Final fallback: return original
            pass
    return nx.to_numpy_array(G).astype(int)

def gate_preserving_fanout(cm: np.ndarray, seed: int | None = None) -> np.ndarray:
    # Preserve per-row out-degree (fan-out). Randomly reassign targets per source.
    rng  = np.random.default_rng(seed)
    n    = cm.shape[0]
    adj  = np.zeros_like(cm, dtype=int)
    cols = np.arange(n)
    for i in range(n):
        k = int(cm[i].sum())
        if k == 0:
            continue
        choices = rng.choice(cols, size=k, replace=False)
        # Optionally avoid self loops similar to original structure
        if k < n and i in choices:
            # swap out self if present
            alt = rng.choice(cols[cols != i])
            choices[choices == i] = alt
        adj[i, choices] = 1
    return adj

def compute_dv2(cm: np.ndarray) -> float:
    enc = UniversalDv2Encoder(cm)
    res = enc.compute()
    return float(res["dv2"])

def load_existing_results() -> List[Dict[str, Any]]:
    if NULL_STATS_FILE.exists():
        try:
            with open(NULL_STATS_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_results(results: List[Dict[str, Any]]):
    # Atomic write to avoid corruption
    temp_file = NULL_STATS_FILE.with_suffix(".tmp")
    with open(temp_file, "w") as f:
        json.dump(results, f, indent=2)
    temp_file.replace(NULL_STATS_FILE)

def process_networks(
    max_networks: int = 200,
    nulls_per_type: int = 1000,
    allow_self_loops: bool = False,
    seed: int | None = 42,
    time_limit_sec: int | None = None
) -> List[Dict]:
    
    start_time = time.time()
    
    # Load existing results (Resume capability)
    results = load_existing_results()
    processed_names = {r["network"] for r in results}
    
    # Load all potential files
    files = sorted([p for p in PROCESSED_DIR.glob("*.json") if p.name not in {"gate_histogram.json", "truth_tables.json"}])
    
    print(f"Loaded {len(results)} existing results. Found {len(files)} total network files.")
    
    count = 0
    
    try:
        for path in files:
            if count >= max_networks:
                break
                
            name, cm, nodes = load_cm(path)
            
            # Skip if already processed with sufficient nulls
            if name in processed_names:
                # Check if existing result has enough nulls
                existing_entry = next((r for r in results if r["network"] == name), None)
                if existing_entry and existing_entry.get("nulls_per_type", 0) >= nulls_per_type:
                    print(f"Skipping {name} (already has {existing_entry['nulls_per_type']} nulls)")
                    continue
                else:
                    print(f"Reprocessing {name} (requested {nulls_per_type} nulls, found {existing_entry.get('nulls_per_type', 0)})")
                    # Remove old entry to avoid duplicates
                    results = [r for r in results if r["network"] != name]

            # Validation filters
            if cm.size == 0 or cm.shape[0] != cm.shape[1]:
                continue
            n = cm.shape[0]
            if n < 5 or n > 100:
                continue

            # Check time limit
            if time_limit_sec and (time.time() - start_time > time_limit_sec):
                print(f"Time limit of {time_limit_sec}s reached. Stopping gracefully.")
                break

            print(f"[{len(results)+1}] Processing {name}: n={n}, E={int(cm.sum())}")
            
            D_bio = compute_dv2(cm)
            null_scores_er   = []
            null_scores_deg  = []
            null_scores_gate = []
            
            for k in range(nulls_per_type):
                # Check time limit inside inner loop for very slow networks
                if time_limit_sec and (time.time() - start_time > time_limit_sec):
                     raise TimeoutException("Time limit reached inside loop")

                s = None if seed is None else seed + k
                # ER edge-shuffle
                cm_er   = er_edge_shuffle(cm, allow_self_loops=allow_self_loops, seed=s)
                null_scores_er.append(compute_dv2(cm_er))
                # Degree-preserving
                cm_deg  = degree_preserving_swap(cm, nswap_factor=10, seed=s)
                null_scores_deg.append(compute_dv2(cm_deg))
                # Gate-preserving (fanout)
                cm_gate = gate_preserving_fanout(cm, seed=s)
                null_scores_gate.append(compute_dv2(cm_gate))
            
            def zscore(x: float, xs: List[float]) -> Tuple[float, float, float]:
                mu = float(np.mean(xs))
                sd = float(np.std(xs)) if len(xs) > 1 else 0.0
                z  = (x - mu) / sd if sd > 0 else 0.0
                return z, mu, sd
            
            z_er,  mu_er,  sd_er  = zscore(D_bio, null_scores_er)
            z_deg, mu_deg, sd_deg = zscore(D_bio, null_scores_deg)
            z_gate,mu_gate,sd_gate= zscore(D_bio, null_scores_gate)
            
            entry = {
                "network": name,
                "nodes": len(nodes),
                "n": n,
                "E": int(cm.sum()),
                "D_bio": D_bio,
                "nulls_per_type": nulls_per_type,
                "z_er": z_er,   "mu_er": mu_er,   "sd_er": sd_er,
                "z_deg": z_deg, "mu_deg": mu_deg, "sd_deg": sd_deg,
                "z_gate": z_gate,"mu_gate":mu_gate,"sd_gate":sd_gate,
                "timestamp": time.time()
            }
            results.append(entry)
            save_results(results) # Checkpoint after each network
            count += 1
            
    except TimeoutException:
        print("Time limit reached. Saving progress...")
    except KeyboardInterrupt:
        print("Interrupted! Saving progress...")
    finally:
        save_results(results)
        
    return results

def main():
    parser = argparse.ArgumentParser(description="Massive Null Model Generator with Checkpointing")
    parser.add_argument("--networks", type=int, default=200, help="Max networks to process")
    parser.add_argument("--nulls", type=int, default=1000, help="Nulls per type per network")
    parser.add_argument("--time_limit", type=int, default=None, help="Time limit in seconds (soft stop)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    
    args = parser.parse_args()

    print(f"=== Phase 3: Massive Null Model Generation ===")
    print(f"Configuration: Max Networks={args.networks}, Nulls={args.nulls}, Time Limit={args.time_limit}s")
    
    results = process_networks(
        max_networks=args.networks,
        nulls_per_type=args.nulls,
        allow_self_loops=False,
        seed=args.seed,
        time_limit_sec=args.time_limit
    )
    
    print(f"Total processed so far: {len(results)}")
    
    # Global summary
    if results:
        z_er   = [r["z_er"] for r in results]
        z_deg  = [r["z_deg"] for r in results]
        z_gate = [r["z_gate"] for r in results]
        summary = {
            "count": len(results),
            "z_er_mean": float(np.mean(z_er)) if z_er else 0.0,
            "z_deg_mean": float(np.mean(z_deg)) if z_deg else 0.0,
            "z_gate_mean": float(np.mean(z_gate)) if z_gate else 0.0
        }
        with open(RESULTS_DIR / "null_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        print(f"Global Z means: ER={summary['z_er_mean']:.3f}, DEG={summary['z_deg_mean']:.3f}, GATE={summary['z_gate_mean']:.3f}")

if __name__ == "__main__":
    main()
