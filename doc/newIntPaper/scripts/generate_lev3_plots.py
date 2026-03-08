import json
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
import sys
from pathlib import Path

# Add src to path
SRC_DIR = Path(__file__).resolve().parents[3] / "src"
sys.path.append(str(SRC_DIR))

from experiments.Null_Generator_HPC import er_edge_shuffle, degree_preserving_swap, gate_preserving_fanout

def load_network(name):
    path = Path(__file__).resolve().parents[3] / "data" / "bio" / "processed" / f"{name}.json"
    with open(path, "r") as f:
        data = json.load(f)
    cm = np.array(data["cm"], dtype=int)
    return cm

def plot_null_comparison(network_name="drosophila_sp"):
    cm = load_network(network_name)
    
    # Generate Nulls
    cm_er = er_edge_shuffle(cm, seed=42)
    cm_deg = degree_preserving_swap(cm, seed=42)
    cm_gate = gate_preserving_fanout(cm, seed=42)
    
    fig, axes = plt.subplots(1, 4, figsize=(20, 5))
    
    titles = ["Original Biological", "Erdős-Rényi (Random)", "Degree-Preserving", "Fan-out Preserving"]
    matrices = [cm, cm_er, cm_deg, cm_gate]
    
    for ax, mat, title in zip(axes, matrices, titles):
        ax.spy(mat, markersize=5, color='black')
        ax.set_title(title, fontsize=14)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlabel(f"Edges: {np.sum(mat)}")
        
    plt.tight_layout()
    output_path = Path(__file__).resolve().parents[1] / "figures" / "null_comparison.png"
    plt.savefig(output_path, dpi=300)
    print(f"Saved null comparison to {output_path}")

def plot_zscore_dist():
    stats_path = Path(__file__).resolve().parents[3] / "results" / "bio" / "null_stats.json"
    if not stats_path.exists():
        print("No stats file found.")
        return

    with open(stats_path, "r") as f:
        data = json.load(f)
        
    z_er = [d["z_er"] for d in data if "z_er" in d]
    z_deg = [d["z_deg"] for d in data if "z_deg" in d]
    z_gate = [d["z_gate"] for d in data if "z_gate" in d]
    
    plt.figure(figsize=(10, 6))
    plt.hist(z_er, bins=30, alpha=0.5, label='Erdős-Rényi', color='gray')
    plt.hist(z_gate, bins=30, alpha=0.5, label='Fan-out Preserving', color='blue')
    plt.hist(z_deg, bins=30, alpha=0.5, label='Degree Preserving', color='red')
    
    plt.axvline(0, color='black', linestyle='--')
    plt.xlabel('Z-Score (Structural Complexity)', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.title('Distribution of Algorithmic Complexity Z-Scores', fontsize=14)
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    output_path = Path(__file__).resolve().parents[1] / "figures" / "zscore_dist.png"
    plt.savefig(output_path, dpi=300)
    print(f"Saved Z-score distribution to {output_path}")

if __name__ == "__main__":
    plot_null_comparison()
    plot_zscore_dist()
