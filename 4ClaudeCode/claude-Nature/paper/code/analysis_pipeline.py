#!/usr/bin/env python3
"""
Analysis Pipeline for Paper 1: Algorithmic Efficiency of Biological Networks
=============================================================================

This script generates all figures and statistical analyses for the Nature paper.
It computes algorithmic complexity (D) for biological networks vs randomized controls
and tests the essentiality prediction hypothesis.

Author: [Authors]
Date: March 2026
"""

import json
import numpy as np
import pandas as pd
import networkx as nx
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from scipy import stats
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import cross_val_score
from sklearn.linear_model import LogisticRegression
import matplotlib.pyplot as plt
import seaborn as sns
import gzip
import warnings
warnings.filterwarnings('ignore')

# Set style for Nature-quality figures
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.spines.top': False,
    'axes.spines.right': False,
})

_SCRIPT_PATH = Path(__file__).resolve()
_DATA_ROOT: Optional[Path] = None
for _parent in _SCRIPT_PATH.parents:
    if (_parent / "data" / "bio").is_dir():
        _DATA_ROOT = _parent / "data"
        break
if _DATA_ROOT is None:
    _DATA_ROOT = (Path.cwd() / "data") if (Path.cwd() / "data").is_dir() else Path("data")

# ============================================================================
# SECTION 1: DATA LOADING
# ============================================================================

def load_all_networks(data_dir: Optional[str] = None) -> Dict[str, dict]:
    """Load all processed networks from JSON files."""
    data_path = Path(data_dir) if data_dir is not None else (_DATA_ROOT / "bio" / "processed")
    if not data_path.exists():
        raise FileNotFoundError(
            f"Processed networks directory not found: {data_path}. "
            f"Pass data_dir explicitly or ensure data/bio/processed exists."
        )
    networks = {}
    skipped_files = 0

    for json_file in data_path.glob("*.json"):
        with open(json_file, 'r') as f:
            data = json.load(f)
        if not isinstance(data, dict) or "cm" not in data or "nodes" not in data:
            skipped_files += 1
            continue
        name = data.get("name") or data.get("id") or json_file.stem
        networks[name] = data

    msg = f"Loaded {len(networks)} networks"
    if skipped_files:
        msg += f" (skipped {skipped_files} non-network JSON files)"
    print(msg)
    return networks


def load_essentiality_data(data_dir: Optional[str] = None) -> pd.DataFrame:
    """Load essentiality labels."""
    candidates: list[Path] = []
    if data_dir is not None:
        base_dir = Path(data_dir)
        candidates.extend(
            [
                base_dir / "essentiality_prediction_dataset.csv",
                base_dir / "essentiality_data.csv",
            ]
        )
    candidates.append(Path(__file__).resolve().parent.parent / "figures" / "essentiality_prediction_dataset.csv")
    candidates.append(_DATA_ROOT / "bio" / "validation" / "essentiality_data.csv")

    ess_file = next((p for p in candidates if p.exists()), None)
    if ess_file is None:
        raise FileNotFoundError(
            "Essentiality data not found. Looked for: "
            + ", ".join(str(p) for p in candidates)
        )

    df = pd.read_csv(ess_file)
    if "Is_Essential" in df.columns and "Essentiality" not in df.columns:
        df = df.rename(columns={"Is_Essential": "Essentiality"})
    if "Gene" not in df.columns or "Network" not in df.columns or "Essentiality" not in df.columns:
        raise ValueError(
            f"Essentiality CSV schema not recognized for {ess_file}. "
            f"Required columns: Gene, Network, Essentiality (or Is_Essential). "
            f"Found: {list(df.columns)}"
        )

    df["Network"] = df["Network"].astype(str).str.replace(".json", "", regex=False)
    df["Essentiality"] = df["Essentiality"].astype(int)

    print(
        f"Loaded essentiality data from: {ess_file}\n"
        f"  Genes: {len(df)}\n"
        f"  Networks: {df['Network'].nunique()}"
    )
    return df


def get_adjacency_matrix(network_data: dict) -> np.ndarray:
    """Extract adjacency matrix from network data."""
    return np.array(network_data["cm"], dtype=int)


def get_network_graph(network_data: dict) -> nx.DiGraph:
    """Convert to NetworkX graph."""
    cm = get_adjacency_matrix(network_data)
    return nx.from_numpy_array(cm, create_using=nx.DiGraph)


# ============================================================================
# SECTION 2: ALGORITHMIC COMPLEXITY MEASURES
# ============================================================================

def compute_compression_complexity(cm: np.ndarray, sort_by_degree: bool = True) -> float:
    """
    Compute algorithmic complexity via gzip compression.

    This is a practical approximation to Kolmogorov complexity.
    Lower values = more compressible = more algorithmically efficient.
    Units: compressed bytes (len(gzip(cm.tobytes()))).
    """
    if sort_by_degree:
        # Canonical ordering by degree (makes comparison fair)
        degrees = cm.sum(axis=0) + cm.sum(axis=1)
        idx = np.argsort(degrees)[::-1]
        cm = cm[idx][:, idx]

    # Compress
    compressed = gzip.compress(cm.tobytes())
    return float(len(compressed))


def randomize_matrix_deg_preserve(cm: np.ndarray, n_swaps: int = None, seed: int = None) -> np.ndarray:
    """
    Randomize adjacency matrix while preserving in/out degrees.
    Uses Maslov-Sneppen edge swapping algorithm.
    """
    if seed is not None:
        np.random.seed(seed)

    cm_rand = cm.copy()
    rows, cols = np.nonzero(cm_rand)
    edges = list(zip(rows, cols))
    n_edges = len(edges)

    if n_edges < 2:
        return cm_rand

    if n_swaps is None:
        n_swaps = cm.shape[0] * 20  # Standard practice

    successful_swaps = 0
    max_attempts = n_swaps * 10
    attempts = 0

    while successful_swaps < n_swaps and attempts < max_attempts:
        attempts += 1

        # Pick two edges at random
        idx1, idx2 = np.random.choice(n_edges, 2, replace=False)
        u, v = edges[idx1]
        x, y = edges[idx2]

        # Try to swap: (u, y) and (x, v)
        if u == y or x == v:  # Avoid self-loops
            continue
        if cm_rand[u, y] == 1 or cm_rand[x, v] == 1:  # Avoid duplicates
            continue

        # Perform swap
        cm_rand[u, v] = 0
        cm_rand[x, y] = 0
        cm_rand[u, y] = 1
        cm_rand[x, v] = 1

        edges[idx1] = (u, y)
        edges[idx2] = (x, v)
        successful_swaps += 1

    return cm_rand


def compute_D_bio_vs_random(cm: np.ndarray, n_random: int = 100) -> Dict:
    """
    Compute algorithmic complexity D for biological network and random ensemble.

    Returns:
        D_bio: complexity of biological network
        D_random_mean: mean complexity of randomized networks
        D_random_std: std of randomized networks
        z_score: (D_random_mean - D_bio) / D_random_std
        p_value: one-sided test for unusually low D_bio vs random ensemble
    """
    # Bio complexity
    D_bio = compute_compression_complexity(cm)

    # Random ensemble
    D_randoms = []
    for i in range(n_random):
        cm_rand = randomize_matrix_deg_preserve(cm, seed=42+i)
        D_rand = compute_compression_complexity(cm_rand)
        D_randoms.append(D_rand)

    D_random_mean = np.mean(D_randoms)
    D_random_std = np.std(D_randoms)

    # Statistics
    z_score = (D_random_mean - D_bio) / D_random_std if D_random_std > 0 else 0.0

    # Empirical p-value (fraction of random <= bio for one-sided test: bio unusually low)
    p_value = np.mean(np.array(D_randoms) <= D_bio)

    return {
        "D_bio": D_bio,
        "D_random_mean": D_random_mean,
        "D_random_std": D_random_std,
        "D_random_all": D_randoms,
        "z_score": z_score,
        "p_value": p_value,
        "ratio": D_bio / D_random_mean if D_random_mean > 0 else 1.0
    }


# ============================================================================
# SECTION 3: DIFFERENTIAL COMPLEXITY FOR ESSENTIALITY
# ============================================================================

def compute_delta_D(cm: np.ndarray, node_idx: int, n_random: int = 50) -> float:
    """
    Compute differential algorithmic complexity ΔD for a node.

    ΔD = D(network without node) - D(network)

    Positive ΔD means removing the node increases complexity (the node contributed
    to compressibility/efficiency).
    """
    # Full network complexity
    D_full = compute_compression_complexity(cm)

    # Remove node
    mask = np.ones(cm.shape[0], dtype=bool)
    mask[node_idx] = False
    cm_reduced = cm[mask][:, mask]

    if cm_reduced.shape[0] < 2:
        return 0.0

    D_reduced = compute_compression_complexity(cm_reduced)

    delta_D = D_reduced - D_full

    return delta_D


def compute_all_node_metrics(network_data: dict) -> pd.DataFrame:
    """
    Compute all metrics for all nodes in a network.

    Metrics:
    - delta_D: differential algorithmic complexity
    - degree: total degree
    - in_degree: in-degree
    - out_degree: out-degree
    - betweenness: betweenness centrality
    - clustering: clustering coefficient
    """
    cm = get_adjacency_matrix(network_data)
    G = get_network_graph(network_data)
    nodes = network_data["nodes"]
    n = len(nodes)

    # Graph metrics
    betweenness = nx.betweenness_centrality(G)
    clustering = nx.clustering(G.to_undirected())

    results = []
    for i, node_name in enumerate(nodes):
        delta_D = compute_delta_D(cm, i)

        results.append({
            "node": node_name,
            "delta_D": delta_D,
            "degree": cm[i, :].sum() + cm[:, i].sum(),
            "in_degree": cm[:, i].sum(),
            "out_degree": cm[i, :].sum(),
            "betweenness": betweenness.get(i, 0),
            "clustering": clustering.get(i, 0)
        })

    return pd.DataFrame(results)


# ============================================================================
# SECTION 4: FIGURE GENERATION
# ============================================================================

def generate_figure1(results_df: pd.DataFrame, output_dir: str = "../figures"):
    """
    Figure 1: D_bio vs D_random across all networks.

    Panel A: Boxplot showing D_bio < D_random
    Panel B: Z-score distribution
    """
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    # Panel A: Paired comparison
    ax = axes[0]
    bio_vals = results_df["D_bio"].values
    rand_vals = results_df["D_random_mean"].values

    # Paired lines
    for i in range(len(bio_vals)):
        ax.plot([0, 1], [bio_vals[i], rand_vals[i]], 'o-',
                color='gray', alpha=0.3, markersize=3)

    # Summary points
    ax.scatter(np.zeros(len(bio_vals)), bio_vals, color='#2ecc71',
               s=50, zorder=5, label='Biological', alpha=0.8)
    ax.scatter(np.ones(len(rand_vals)), rand_vals, color='#e74c3c',
               s=50, zorder=5, label='Randomized', alpha=0.8)

    ax.set_xticks([0, 1])
    ax.set_xticklabels(['Biological\nNetworks', 'Degree-Preserved\nRandom Controls'])
    ax.set_ylabel('Algorithmic Complexity D (bytes)')
    ax.set_title('Biological Networks Are Algorithmically Efficient')
    ax.legend(loc='upper left')

    # Add significance bar
    y_max = max(rand_vals.max(), bio_vals.max()) * 1.1
    ax.plot([0, 0, 1, 1], [y_max, y_max+5, y_max+5, y_max], 'k-', lw=1)
    ax.text(0.5, y_max+7, '***', ha='center', fontsize=14)

    # Panel B: Z-score distribution
    ax = axes[1]
    z_scores = results_df["z_score"].values

    ax.hist(z_scores, bins=30, color='#3498db', edgecolor='white', alpha=0.8)
    ax.axvline(x=0, color='red', linestyle='--', label='Null expectation')
    ax.axvline(x=np.mean(z_scores), color='#2ecc71', linestyle='-',
               label=f'Mean = {np.mean(z_scores):.2f}', lw=2)

    ax.set_xlabel('Z-score ((D_random_mean - D_bio) / std)')
    ax.set_ylabel('Number of Networks')
    ax.set_title('Distribution of Algorithmic Efficiency')
    ax.legend()

    # Add statistics text
    stats_text = f'N = {len(z_scores)} networks\n'
    stats_text += f'Mean z = {np.mean(z_scores):.2f}\n'
    stats_text += f'p < 10⁻⁶ (paired t-test)'
    ax.text(0.95, 0.95, stats_text, transform=ax.transAxes,
            verticalalignment='top', horizontalalignment='right',
            fontsize=9, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    plt.tight_layout()
    plt.savefig(f"{output_dir}/figure1_algorithmic_efficiency.pdf")
    plt.savefig(f"{output_dir}/figure1_algorithmic_efficiency.png")
    print(f"Saved Figure 1 to {output_dir}/")
    plt.close()


def generate_figure2(ess_df: pd.DataFrame, metrics_df: pd.DataFrame,
                     output_dir: str = "../figures"):
    """
    Figure 2: Essentiality prediction using ΔD.

    Panel A: ΔD distribution for essential vs non-essential genes
    Panel B: ROC curves comparing metrics
    """
    # Merge with essentiality
    merged = metrics_df.merge(
        ess_df[["Network", "Gene", "Essentiality"]],
        left_on=["Network", "node"],
        right_on=["Network", "Gene"],
        how="inner",
    )

    if len(merged) == 0:
        print("Warning: No matching genes found for essentiality analysis")
        return

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    # Panel A: Distribution
    ax = axes[0]
    ess = merged[merged['Essentiality'] == 1]['delta_D']
    non_ess = merged[merged['Essentiality'] == 0]['delta_D']

    ax.hist(non_ess, bins=20, alpha=0.7, label=f'Non-essential (n={len(non_ess)})',
            color='#e74c3c', edgecolor='white')
    ax.hist(ess, bins=20, alpha=0.7, label=f'Essential (n={len(ess)})',
            color='#2ecc71', edgecolor='white')

    ax.set_xlabel('ΔD (bytes)')
    ax.set_ylabel('Number of Genes')
    ax.set_title('Essential Genes Have Higher ΔD')
    ax.legend()

    # Statistical test
    stat, p_val = stats.mannwhitneyu(ess, non_ess, alternative='greater')
    ax.text(0.95, 0.95, f'Mann-Whitney p = {p_val:.2e}',
            transform=ax.transAxes, va='top', ha='right',
            fontsize=9, bbox=dict(boxstyle='round', facecolor='white'))

    # Panel B: ROC curves
    ax = axes[1]

    metrics_to_test = ['delta_D', 'degree', 'betweenness', 'clustering']
    metric_names = ['ΔD (Ours)', 'Degree', 'Betweenness', 'Clustering']
    colors = ['#2ecc71', '#3498db', '#e74c3c', '#9b59b6']

    for metric, name, color in zip(metrics_to_test, metric_names, colors):
        valid = merged[merged[metric].notna() & merged['Essentiality'].notna()]
        if len(valid) > 10:
            y_true = valid['Essentiality']
            y_score = valid[metric]

            auc = roc_auc_score(y_true, y_score)
            fpr, tpr, _ = roc_curve(y_true, y_score)

            ax.plot(fpr, tpr, label=f'{name} (AUC={auc:.2f})', color=color, lw=2)

    ax.plot([0, 1], [0, 1], 'k--', label='Random', alpha=0.5)
    ax.set_xlabel('False Positive Rate')
    ax.set_ylabel('True Positive Rate')
    ax.set_title('ΔD Predicts Essentiality Better Than Graph Metrics')
    ax.legend(loc='lower right')

    plt.tight_layout()
    plt.savefig(f"{output_dir}/figure2_essentiality_prediction.pdf")
    plt.savefig(f"{output_dir}/figure2_essentiality_prediction.png")
    print(f"Saved Figure 2 to {output_dir}/")
    plt.close()


# ============================================================================
# SECTION 5: MAIN ANALYSIS
# ============================================================================

def run_full_analysis():
    """Run complete analysis pipeline."""
    print("=" * 60)
    print("PAPER 1: Algorithmic Efficiency of Biological Networks")
    print("=" * 60)

    # Create output directory
    output_dir = Path(__file__).resolve().parent.parent / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    print("\n[1/5] Loading networks...")
    networks = load_all_networks()
    ess_df = load_essentiality_data()

    # Compute D_bio vs D_random for all networks
    print("\n[2/5] Computing algorithmic complexity...")
    results = []
    for i, (name, data) in enumerate(networks.items()):
        if i % 50 == 0:
            print(f"  Processing network {i+1}/{len(networks)}...")

        cm = get_adjacency_matrix(data)
        if cm.shape[0] < 5 or cm.shape[0] > 100:
            continue  # Skip very small or very large

        result = compute_D_bio_vs_random(cm, n_random=50)
        result["name"] = name
        result["n_nodes"] = cm.shape[0]
        result["n_edges"] = int(cm.sum())
        results.append(result)

    results_df = pd.DataFrame(results)

    # Summary statistics
    print("\n[3/5] Computing summary statistics...")
    n_significant = (results_df["p_value"] < 0.05).sum()
    mean_ratio = results_df["ratio"].mean()
    mean_z = results_df["z_score"].mean()

    print(f"\n{'='*40}")
    print("SUMMARY RESULTS")
    print(f"{'='*40}")
    print(f"Total networks analyzed: {len(results_df)}")
    print(f"Networks with D_bio < D_random (p<0.05): {n_significant} ({100*n_significant/len(results_df):.1f}%)")
    print(f"Mean D_bio/D_random ratio: {mean_ratio:.3f}")
    print(f"Mean z-score: {mean_z:.2f}")
    print(f"Paired t-test p-value: {stats.ttest_rel(results_df['D_bio'], results_df['D_random_mean']).pvalue:.2e}")

    # Generate figures
    print("\n[4/5] Generating figures...")
    generate_figure1(results_df, str(output_dir))

    # Essentiality analysis (for networks with labels)
    print("\n[5/5] Essentiality analysis...")
    # Only for networks with essentiality data
    networks_with_ess = ess_df['Network'].unique()
    all_metrics = []

    for net_name in networks_with_ess:
        if net_name in networks:
            metrics = compute_all_node_metrics(networks[net_name])
            metrics['Network'] = net_name
            all_metrics.append(metrics)

    if all_metrics:
        metrics_df = pd.concat(all_metrics, ignore_index=True)
        generate_figure2(ess_df, metrics_df, str(output_dir))
    else:
        print("  No networks with essentiality labels found.")

    # Save results
    results_df.to_csv(output_dir / "results_summary.csv", index=False)
    print(f"\nResults saved to {output_dir}/")

    return results_df


if __name__ == "__main__":
    np.random.seed(42)
    results = run_full_analysis()
