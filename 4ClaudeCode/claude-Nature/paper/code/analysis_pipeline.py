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
import argparse
import os
import sys
import subprocess
import numpy as np
import pandas as pd
import networkx as nx
import hashlib
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from scipy import stats
from sklearn.metrics import (
    roc_auc_score,
    roc_curve,
    precision_recall_curve,
    average_precision_score,
    brier_score_loss,
)
from sklearn.model_selection import cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
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


def _repo_root() -> Path:
    for parent in _SCRIPT_PATH.parents:
        if (parent / "src").is_dir() and (parent / "results").is_dir():
            return parent
    return _SCRIPT_PATH.parents[2]


def _paper_figures_dir() -> Path:
    return _SCRIPT_PATH.parent.parent / "figures"


def _load_json(path: Path) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def _bootstrap_auc(
    y: np.ndarray,
    score: np.ndarray,
    n_boot: int,
    rng: np.random.Generator,
) -> tuple[float, float, float, np.ndarray]:
    base_auc = float(roc_auc_score(y, score))
    idx = np.arange(len(y))
    boot = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        sample = rng.choice(idx, size=len(idx), replace=True)
        boot[i] = roc_auc_score(y[sample], score[sample])
    lo, hi = np.quantile(boot, [0.025, 0.975])
    return base_auc, float(lo), float(hi), boot


def _bootstrap_grouped_metric(
    y: np.ndarray,
    score: np.ndarray,
    groups: np.ndarray,
    n_boot: int,
    seed: int,
    metric: str,
) -> tuple[float, float, float, np.ndarray]:
    y = np.asarray(y).astype(int)
    score = np.asarray(score).astype(float)
    groups = np.asarray(groups).astype(str)

    uniq = np.unique(groups)
    rng = np.random.default_rng(seed)

    group_to_idx = {g: np.where(groups == g)[0] for g in uniq}
    boot = np.empty(n_boot, dtype=float)
    filled = 0
    attempts = 0
    max_attempts = n_boot * 50

    def _metric(ys: np.ndarray, ss: np.ndarray) -> float:
        if metric == "auc":
            return float(roc_auc_score(ys, ss))
        if metric == "ap":
            return float(average_precision_score(ys, ss))
        raise ValueError(f"Unknown metric: {metric}")

    while filled < n_boot and attempts < max_attempts:
        attempts += 1
        sampled_groups = rng.choice(uniq, size=len(uniq), replace=True)
        sample_idx = np.concatenate([group_to_idx[g] for g in sampled_groups], axis=0)
        ys = y[sample_idx]
        if len(np.unique(ys)) < 2:
            continue
        ss = score[sample_idx]
        boot[filled] = _metric(ys, ss)
        filled += 1

    if filled == 0:
        return float("nan"), float("nan"), float("nan"), np.array([], dtype=float)

    boot = boot[:filled]
    lo, hi = np.quantile(boot, [0.025, 0.975])
    base = _metric(y, score) if len(np.unique(y)) >= 2 else float("nan")
    return base, float(lo), float(hi), boot


def _paired_bootstrap_pvalue(delta: np.ndarray) -> float:
    delta = np.asarray(delta, dtype=float)
    delta = delta[np.isfinite(delta)]
    if delta.size == 0:
        return float("nan")
    p_pos = float(np.mean(delta > 0))
    p_neg = float(np.mean(delta < 0))
    return float(2 * min(p_pos, p_neg))


def _bootstrap_grouped_brier(
    y: np.ndarray,
    prob: np.ndarray,
    groups: np.ndarray,
    n_boot: int,
    seed: int,
) -> tuple[float, float, float, np.ndarray]:
    y = np.asarray(y).astype(int)
    prob = np.asarray(prob).astype(float)
    groups = np.asarray(groups).astype(str)

    uniq = np.unique(groups)
    rng = np.random.default_rng(seed)

    group_to_idx = {g: np.where(groups == g)[0] for g in uniq}
    boot = np.empty(n_boot, dtype=float)
    filled = 0
    attempts = 0
    max_attempts = n_boot * 50

    while filled < n_boot and attempts < max_attempts:
        attempts += 1
        sampled_groups = rng.choice(uniq, size=len(uniq), replace=True)
        sample_idx = np.concatenate([group_to_idx[g] for g in sampled_groups], axis=0)
        ys = y[sample_idx]
        if len(np.unique(ys)) < 2:
            continue
        boot[filled] = float(brier_score_loss(ys, prob[sample_idx]))
        filled += 1

    if filled == 0:
        return float("nan"), float("nan"), float("nan"), np.array([], dtype=float)

    boot = boot[:filled]
    lo, hi = np.quantile(boot, [0.025, 0.975])
    base = float(brier_score_loss(y, prob))
    return base, float(lo), float(hi), boot


def _calibration_bins(prob: np.ndarray, y: np.ndarray, n_bins: int = 10) -> dict:
    prob = np.asarray(prob, dtype=float)
    y = np.asarray(y, dtype=int)

    mask = np.isfinite(prob)
    prob = prob[mask]
    y = y[mask]
    if prob.size == 0:
        return {"n_bins": int(n_bins), "bin_edges": [], "mean_pred": [], "frac_pos": [], "counts": []}

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    mean_pred = []
    frac_pos = []
    counts = []
    for i in range(n_bins):
        lo = edges[i]
        hi = edges[i + 1]
        in_bin = (prob >= lo) & (prob < hi if i < (n_bins - 1) else prob <= hi)
        if not np.any(in_bin):
            mean_pred.append(float("nan"))
            frac_pos.append(float("nan"))
            counts.append(0)
            continue
        p = prob[in_bin]
        yy = y[in_bin]
        mean_pred.append(float(np.mean(p)))
        frac_pos.append(float(np.mean(yy)))
        counts.append(int(in_bin.sum()))

    return {
        "n_bins": int(n_bins),
        "bin_edges": [float(x) for x in edges.tolist()],
        "mean_pred": mean_pred,
        "frac_pos": frac_pos,
        "counts": counts,
    }


def _group_stratified_folds(groups: np.ndarray, y: np.ndarray, n_splits: int, seed: int) -> list[tuple[np.ndarray, np.ndarray]]:
    groups = np.asarray(groups).astype(str)
    y = np.asarray(y).astype(int)
    uniq = np.unique(groups)

    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(uniq))
    uniq = uniq[perm]

    pos_per_group = {g: int(y[groups == g].sum()) for g in uniq}
    size_per_group = {g: int((groups == g).sum()) for g in uniq}

    order = sorted(uniq, key=lambda g: (pos_per_group[g], size_per_group[g]), reverse=True)

    fold_groups: list[list[str]] = [[] for _ in range(n_splits)]
    fold_pos = [0 for _ in range(n_splits)]
    fold_size = [0 for _ in range(n_splits)]

    for g in order:
        k = int(min(range(n_splits), key=lambda i: (fold_pos[i], fold_size[i])))
        fold_groups[k].append(g)
        fold_pos[k] += pos_per_group[g]
        fold_size[k] += size_per_group[g]

    splits: list[tuple[np.ndarray, np.ndarray]] = []
    for k in range(n_splits):
        test_groups = np.array(fold_groups[k], dtype=str)
        test_mask = np.isin(groups, test_groups)
        train_idx = np.where(~test_mask)[0]
        test_idx = np.where(test_mask)[0]
        splits.append((train_idx, test_idx))
    return splits


def _node_baselines(network_data: dict) -> pd.DataFrame:
    cm = get_adjacency_matrix(network_data)
    nodes = network_data.get("nodes", [])
    if not isinstance(nodes, list) or len(nodes) != cm.shape[0]:
        nodes = [str(i) for i in range(cm.shape[0])]

    G = nx.from_numpy_array(cm, create_using=nx.DiGraph)
    Gu = G.to_undirected()
    closeness = nx.closeness_centrality(Gu)

    try:
        eigen = nx.eigenvector_centrality_numpy(Gu)
    except Exception:
        eigen = {i: float("nan") for i in range(cm.shape[0])}

    out = pd.DataFrame(
        {
            "Gene": [str(n) for n in nodes],
            "Closeness": [float(closeness.get(i, float("nan"))) for i in range(cm.shape[0])],
            "Eigenvector": [float(eigen.get(i, float("nan"))) for i in range(cm.shape[0])],
        }
    )
    return out


def _depmap_gene_feature_means(genes: list[str]) -> pd.DataFrame:
    depmap_dir = _DATA_ROOT / "DepMap"
    expr_path = depmap_dir / "OmicsExpressionProteinCodingGenesTPMLogp1BatchCorrected.csv"
    cn_path = depmap_dir / "OmicsCNGene.csv"

    genes = sorted({str(g) for g in genes})
    out = pd.DataFrame({"Gene": genes})

    def _means_from_matrix(path: Path, prefix: str) -> pd.DataFrame:
        if not path.exists():
            return pd.DataFrame({"Gene": genes, f"{prefix}_mean": [float("nan")] * len(genes)})

        header = pd.read_csv(path, nrows=0)
        cols = list(header.columns)
        if len(cols) < 2:
            return pd.DataFrame({"Gene": genes, f"{prefix}_mean": [float("nan")] * len(genes)})

        first_col = cols[0]
        symbol_to_col = {}
        for c in cols[1:]:
            sym = str(c).split(" (", 1)[0]
            if sym not in symbol_to_col:
                symbol_to_col[sym] = c

        selected = [symbol_to_col[g] for g in genes if g in symbol_to_col]
        if len(selected) == 0:
            return pd.DataFrame({"Gene": genes, f"{prefix}_mean": [float("nan")] * len(genes)})

        mat = pd.read_csv(path, usecols=[first_col] + selected)
        means = mat[selected].mean(axis=0, skipna=True)
        g_means = {str(col).split(" (", 1)[0]: float(means[col]) for col in selected}

        return pd.DataFrame({"Gene": genes, f"{prefix}_mean": [float(g_means.get(g, float("nan"))) for g in genes]})

    expr = _means_from_matrix(expr_path, "DepMapExpr")
    cn = _means_from_matrix(cn_path, "DepMapCN")
    out = out.merge(expr, on="Gene", how="left").merge(cn, on="Gene", how="left")
    return out


def _gnomad_constraint_features(genes: list[str]) -> pd.DataFrame:
    gnomad_dir = _DATA_ROOT / "gnomAD"
    data_path = gnomad_dir / "gnomad_v2.1.1_constraint.tsv.bgz"
    sha_path = gnomad_dir / "gnomad_v2.1.1_constraint.sha256"

    genes = sorted({str(g) for g in genes})
    out = pd.DataFrame({"Gene": genes})
    if not data_path.exists():
        out["gnomAD_pLI"] = float("nan")
        out["gnomAD_LOEUF"] = float("nan")
        return out

    expected = None
    if sha_path.exists():
        parts = sha_path.read_text().strip().split()
        if parts:
            expected = parts[0].lower()

    if expected is not None:
        h = hashlib.sha256()
        with data_path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        actual = h.hexdigest().lower()
        if actual != expected:
            raise ValueError(f"gnomAD constraint checksum mismatch for {data_path}")

    cols = pd.read_csv(data_path, sep="\t", compression="gzip", nrows=0).columns.tolist()
    required = ["gene", "pLI", "oe_lof_upper"]
    missing = [c for c in required if c not in cols]
    if missing:
        out["gnomAD_pLI"] = float("nan")
        out["gnomAD_LOEUF"] = float("nan")
        return out

    use = ["gene", "pLI", "oe_lof_upper"]
    tbl = pd.read_csv(data_path, sep="\t", compression="gzip", usecols=use)
    tbl = tbl.rename(columns={"gene": "Gene", "pLI": "gnomAD_pLI_raw", "oe_lof_upper": "gnomAD_LOEUF_raw"})
    tbl["Gene"] = tbl["Gene"].astype(str)
    tbl["gnomAD_pLI_raw"] = pd.to_numeric(tbl["gnomAD_pLI_raw"], errors="coerce")
    tbl["gnomAD_LOEUF_raw"] = pd.to_numeric(tbl["gnomAD_LOEUF_raw"], errors="coerce")

    agg = (
        tbl.groupby("Gene", as_index=False)
        .agg(
            gnomAD_pLI=("gnomAD_pLI_raw", "max"),
            gnomAD_LOEUF=("gnomAD_LOEUF_raw", "min"),
        )
        .copy()
    )
    out = out.merge(agg, on="Gene", how="left")
    return out

def _infer_source(network_name: str, network_data: Optional[dict]) -> str:
    if isinstance(network_data, dict):
        src = network_data.get("source")
        if isinstance(src, str) and src.strip():
            return src.strip()

    n = str(network_name).lower()
    if n.startswith("ginsim_"):
        return "GINsim"
    if n.startswith("biomodels_"):
        return "BioModels"
    if n.startswith("pyboolnet_"):
        return "PyBoolNet"
    return "Literature"


def _infer_organism_group(network_name: str, network_data: Optional[dict]) -> str:
    if isinstance(network_data, dict):
        for key in ("organism_group", "organism", "species"):
            v = network_data.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()

    n = str(network_name).lower()
    rules = [
        ("yeast", "Yeast"),
        ("saccharomyces", "Yeast"),
        ("drosophila", "Drosophila"),
        ("zebrafish", "Zebrafish"),
        ("danio", "Zebrafish"),
        ("arabidopsis", "Plant"),
        ("plant", "Plant"),
        ("human", "Mammal"),
        ("mouse", "Mammal"),
        ("mammal", "Mammal"),
        ("rat", "Mammal"),
        ("e_coli", "Bacteria"),
        ("escherichia", "Bacteria"),
        ("bacteria", "Bacteria"),
        ("bacillus", "Bacteria"),
    ]
    for token, label in rules:
        if token in n:
            return label
    return "Unknown"


def _size_bin(n_nodes: Optional[float]) -> str:
    if n_nodes is None or not np.isfinite(n_nodes):
        return "Unknown"
    n = int(n_nodes)
    if n <= 10:
        return "5-10"
    if n <= 30:
        return "11-30"
    if n <= 60:
        return "31-60"
    if n <= 100:
        return "61-100"
    return "100+"


def _annotate_essentiality(df: pd.DataFrame, networks: Dict[str, dict]) -> pd.DataFrame:
    meta = []
    for name, data in networks.items():
        cm = data.get("cm")
        n_nodes = float(len(data.get("nodes", []))) if isinstance(data.get("nodes"), list) else float("nan")
        if isinstance(cm, list) and len(cm) > 0:
            n_nodes = float(len(cm))
        meta.append(
            {
                "Network": str(name),
                "Source": _infer_source(name, data),
                "Organism_Group": _infer_organism_group(name, data),
                "N_nodes": n_nodes,
            }
        )
    meta_df = pd.DataFrame(meta)
    meta_df["Size_Bin"] = meta_df["N_nodes"].apply(_size_bin)
    out = df.merge(meta_df, on="Network", how="left")
    out["Source"] = out["Source"].fillna("Unknown")
    out["Organism_Group"] = out["Organism_Group"].fillna("Unknown")
    out["Size_Bin"] = out["Size_Bin"].fillna("Unknown")
    return out

def evaluate_gate_thresholds(
    figures_dir: Optional[str] = None,
    n_boot: int = 10000,
    seed: int = 42,
    reproducibility_networks: int = 30,
) -> pd.DataFrame:
    repo_root = _repo_root()
    fig_dir = Path(figures_dir) if figures_dir is not None else _paper_figures_dir()

    results_summary_path = fig_dir / "results_summary.csv"
    depmap_stats_path = fig_dir / "figure3_depmap_validation_stats.json"
    essentiality_path = repo_root / "results" / "bio" / "essentiality_prediction_dataset.csv"
    corruption_path = repo_root / "results" / "cancer" / "corruption_metrics.csv"

    rows: list[dict] = []

    rs = pd.read_csv(results_summary_path)
    z = rs["z_score"].astype(float).to_numpy()
    p = rs["p_value"].astype(float).to_numpy()
    frac_pos = float(np.mean(z > 0))
    frac_sig = float(np.mean(p <= 0.05))
    mean_z = float(np.mean(z))
    median_z = float(np.median(z))

    gate_a_min_mean_z = 0.5
    gate_a_min_frac_pos = 0.6
    gate_a_min_frac_sig = 0.15

    rows.append(
        {
            "Gate": "A",
            "Criterion": "Null efficiency directionality",
            "Threshold": f"mean(z) ≥ {gate_a_min_mean_z:.2f}",
            "Observed": f"{mean_z:.3f} (median {median_z:.3f})",
            "Pass": mean_z >= gate_a_min_mean_z,
            "Notes": f"n={len(z)}; z>0={frac_pos:.3f}; p≤0.05={frac_sig:.3f}",
        }
    )
    rows.append(
        {
            "Gate": "A",
            "Criterion": "Null efficiency prevalence",
            "Threshold": f"Pr(z>0) ≥ {gate_a_min_frac_pos:.2f}",
            "Observed": f"{frac_pos:.3f}",
            "Pass": frac_pos >= gate_a_min_frac_pos,
            "Notes": "",
        }
    )
    rows.append(
        {
            "Gate": "A",
            "Criterion": "Null efficiency significance rate",
            "Threshold": f"Pr(p≤0.05) ≥ {gate_a_min_frac_sig:.2f}",
            "Observed": f"{frac_sig:.3f}",
            "Pass": frac_sig >= gate_a_min_frac_sig,
            "Notes": "Per-network one-sided empirical p-value against degree-preserved null.",
        }
    )

    gate_a_seed1 = 42
    gate_a_seed2 = 314159
    gate_a_min_spearman = 0.90
    gate_a_max_abs_mean_z_diff = 0.10
    gate_a_min_sign_agreement = 0.90

    networks = load_all_networks()
    eligible: list[str] = []
    for name, data in networks.items():
        cm = get_adjacency_matrix(data)
        if 5 <= cm.shape[0] <= 100:
            eligible.append(name)
    eligible = sorted(eligible)
    sample = eligible[: max(0, min(reproducibility_networks, len(eligible)))]

    z1 = []
    z2 = []
    for name in sample:
        cm = get_adjacency_matrix(networks[name])
        z1.append(compute_D_bio_vs_random(cm, n_random=50, seed_base=gate_a_seed1)["z_score"])
        z2.append(compute_D_bio_vs_random(cm, n_random=50, seed_base=gate_a_seed2)["z_score"])
    z1 = np.asarray(z1, dtype=float)
    z2 = np.asarray(z2, dtype=float)

    if len(sample) >= 5:
        rho = float(stats.spearmanr(z1, z2).correlation)
    else:
        rho = float("nan")
    mean_diff = float(np.mean(z2) - np.mean(z1)) if len(sample) else float("nan")
    sign_agree = float(np.mean(np.sign(z1) == np.sign(z2))) if len(sample) else float("nan")

    rows.append(
        {
            "Gate": "A",
            "Criterion": "Seed robustness (z ranks + mean)",
            "Threshold": f"Spearman(z) ≥ {gate_a_min_spearman:.2f}, |Δmean(z)| ≤ {gate_a_max_abs_mean_z_diff:.2f}, sign≥{gate_a_min_sign_agreement:.2f}",
            "Observed": f"n={len(sample)}; Spearman={rho:.3f}; Δmean(z)={mean_diff:.3f}; sign={sign_agree:.3f}",
            "Pass": (len(sample) >= 5)
            and (rho >= gate_a_min_spearman)
            and (abs(mean_diff) <= gate_a_max_abs_mean_z_diff)
            and (sign_agree >= gate_a_min_sign_agreement),
            "Notes": f"Recomputed on fixed subset (first {len(sample)} eligible networks) with seed_base={gate_a_seed1} vs {gate_a_seed2}, n_random=50.",
        }
    )

    gate_b_min_independent_cohorts = 1
    gate_b_min_networks_per_cohort = 100
    gate_b_required_sensitivity_axes = 3
    rows.append(
        {
            "Gate": "B",
            "Criterion": "Independent cohort replication",
            "Threshold": f"≥{gate_b_min_independent_cohorts} independent cohort with ≥{gate_b_min_networks_per_cohort} networks passing size filters",
            "Observed": "N/A (not implemented in this checkout)",
            "Pass": False,
            "Notes": "Independence requires non-overlapping acquisition/curation pipeline; criteria evaluated with the same Gate A contract.",
        }
    )
    rows.append(
        {
            "Gate": "B",
            "Criterion": "Sensitivity analysis suite",
            "Threshold": f"≥{gate_b_required_sensitivity_axes} perturbation axes reported; Gate A remains PASS in ≥2/3",
            "Observed": "N/A (not implemented in this checkout)",
            "Pass": False,
            "Notes": "Perturbation axes are pre-registered (null size, swap budget, ordering); failures must be explained or trigger Gate A rework.",
        }
    )

    if depmap_stats_path.exists():
        dep = _load_json(depmap_stats_path)
        r = float(dep.get("rho", float("nan")))
        pval = float(dep.get("pval", float("nan")))
        n_nodes = int(dep.get("n", 0) or 0)
        gate_c_min_n = 50
        gate_c_min_abs_r = 0.3
        gate_c_max_p = 0.01
        rows.append(
            {
                "Gate": "C",
                "Criterion": "DepMap external anchor",
                "Threshold": f"n≥{gate_c_min_n}, |r|≥{gate_c_min_abs_r:.2f}, p≤{gate_c_max_p:.2g}",
                "Observed": f"n={n_nodes}, r={r:.3f}, p={pval:.3f}",
                "Pass": (n_nodes >= gate_c_min_n) and (abs(r) >= gate_c_min_abs_r) and (pval <= gate_c_max_p),
                "Notes": "Current checkout uses 10-node EGFR scaffold; treated as pilot only.",
            }
        )
    else:
        rows.append(
            {
                "Gate": "C",
                "Criterion": "DepMap external anchor",
                "Threshold": "n≥50, |r|≥0.30, p≤0.01",
                "Observed": "missing figure3_depmap_validation_stats.json",
                "Pass": False,
                "Notes": "",
            }
        )

    ess = pd.read_csv(essentiality_path)
    y = ess["Is_Essential"].astype(int).to_numpy()
    rng = np.random.default_rng(seed)
    auc_dd, dd_lo, dd_hi, dd_boot = _bootstrap_auc(y, ess["Delta_D"].to_numpy(), n_boot=n_boot, rng=rng)
    auc_dd_neg = float(roc_auc_score(y, -ess["Delta_D"].to_numpy()))
    auc_deg, deg_lo, deg_hi, deg_boot = _bootstrap_auc(y, ess["Degree"].to_numpy(), n_boot=n_boot, rng=rng)

    delta_auc = auc_dd - auc_deg
    delta_boot = dd_boot - deg_boot
    delta_lo, delta_hi = np.quantile(delta_boot, [0.025, 0.975])

    gate_c_min_delta_auc = 0.05
    rows.append(
        {
            "Gate": "C",
            "Criterion": "Essentiality incremental value",
            "Threshold": f"ΔAUC(ΔD−Degree) ≥ {gate_c_min_delta_auc:.2f} with 95% CI > 0",
            "Observed": f"ΔAUC={delta_auc:.3f} (95% CI [{delta_lo:.3f},{delta_hi:.3f}]); AUCΔD={auc_dd:.3f} [{dd_lo:.3f},{dd_hi:.3f}] (AUC−ΔD={auc_dd_neg:.3f}) vs AUCdeg={auc_deg:.3f} [{deg_lo:.3f},{deg_hi:.3f}]",
            "Pass": (delta_auc >= gate_c_min_delta_auc) and (delta_lo > 0),
            "Notes": (
                f"Bootstrap resampling over genes (n={len(ess)}; seed={seed}; n_boot={n_boot})."
                + (" AUC(-ΔD) > AUC(ΔD); check ΔD sign convention." if auc_dd_neg > (auc_dd + 1e-12) else "")
            ),
        }
    )

    cor = pd.read_csv(corruption_path)
    diffs = cor["Delta_D"].astype(float).to_numpy()
    mean_delta = float(np.mean(diffs))
    sd_delta = float(np.std(diffs, ddof=1))
    t_res = stats.ttest_1samp(diffs, popmean=0.0, alternative="less")
    d = mean_delta / sd_delta if sd_delta > 0 else float("nan")

    gate_c_max_mean_delta = -1.0
    gate_c_max_paired_p = 1e-6
    gate_c_min_abs_d = 0.5
    rows.append(
        {
            "Gate": "C",
            "Criterion": "Paired tumor/normal corruption",
            "Threshold": f"mean(ΔD^(v2)) ≤ {gate_c_max_mean_delta:.1f} bits, p≤{gate_c_max_paired_p:.0e}, |d|≥{gate_c_min_abs_d:.1f}",
            "Observed": f"mean={mean_delta:.3f} bits; d={d:.3f}; p={float(t_res.pvalue):.2e} (n={len(diffs)})",
            "Pass": (mean_delta <= gate_c_max_mean_delta) and (float(t_res.pvalue) <= gate_c_max_paired_p) and (abs(d) >= gate_c_min_abs_d),
            "Notes": "Current cohort is synthetic in this checkout; numerical signal is not treated as Gate C pass.",
        }
    )

    out = pd.DataFrame(rows)
    out_path = fig_dir / "gate_thresholds_summary.csv"
    out.to_csv(out_path, index=False)

    gate_order = ["A", "B", "C"]
    summary = out.groupby("Gate")["Pass"].agg(["mean", "count"]).reindex(gate_order).fillna(0)
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.bar(summary.index, summary["mean"], color=["#2ecc71", "#f1c40f", "#e74c3c"])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Pass fraction (criteria)")
    ax.set_title("Gate criteria status (frozen thresholds)")
    for i, (gate, row) in enumerate(summary.iterrows()):
        ax.text(i, row["mean"] + 0.03, f"{row['mean']:.2f} ({int(row['count'])})", ha="center", va="bottom", fontsize=9)
    plt.tight_layout()
    plt.savefig(fig_dir / "gate_thresholds_status.png")
    plt.savefig(fig_dir / "gate_thresholds_status.pdf")
    plt.close()

    print(f"Wrote: {out_path}")
    print(f"Wrote: {fig_dir / 'gate_thresholds_status.png'}")

    return out


def load_essentiality_data(data_dir: Optional[str] = None) -> pd.DataFrame:
    """Load essentiality labels."""
    repo_root = _repo_root()
    candidates: list[Path] = []
    if data_dir is not None:
        base_dir = Path(data_dir)
        candidates.extend(
            [
                base_dir / "essentiality_prediction_dataset.csv",
                base_dir / "essentiality_data.csv",
            ]
        )
    candidates.append(repo_root / "results" / "bio" / "essentiality_prediction_dataset.csv")
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

def _wl_tiebreak_keys(cm: np.ndarray, n_iter: int = 4) -> np.ndarray:
    n = int(cm.shape[0])
    if n == 0:
        return np.zeros(0, dtype=np.uint64)

    out_deg = cm.sum(axis=1).astype(np.int64, copy=False)
    in_deg = cm.sum(axis=0).astype(np.int64, copy=False)
    labels = np.empty(n, dtype=np.uint64)
    for i in range(n):
        h = hashlib.blake2b(digest_size=8)
        h.update(np.int64(out_deg[i]).tobytes())
        h.update(np.int64(in_deg[i]).tobytes())
        labels[i] = np.frombuffer(h.digest(), dtype=np.uint64)[0]

    for _ in range(int(n_iter)):
        new_labels = np.empty(n, dtype=np.uint64)
        for i in range(n):
            out_idx = np.flatnonzero(cm[i]).astype(np.int64, copy=False)
            in_idx = np.flatnonzero(cm[:, i]).astype(np.int64, copy=False)
            out_lab = np.sort(labels[out_idx]) if out_idx.size else np.zeros(0, dtype=np.uint64)
            in_lab = np.sort(labels[in_idx]) if in_idx.size else np.zeros(0, dtype=np.uint64)

            h = hashlib.blake2b(digest_size=8)
            h.update(labels[i].tobytes())
            h.update(np.int64(out_lab.size).tobytes())
            if out_lab.size:
                h.update(out_lab.tobytes())
            h.update(np.int64(in_lab.size).tobytes())
            if in_lab.size:
                h.update(in_lab.tobytes())
            new_labels[i] = np.frombuffer(h.digest(), dtype=np.uint64)[0]
        labels = new_labels

    return labels


def compute_compression_complexity(cm: np.ndarray, sort_by_degree: bool = True, tie_breaker: str = "index") -> float:
    """
    Compute algorithmic complexity via gzip compression.

    This is a practical approximation to Kolmogorov complexity.
    Lower values = more compressible = more algorithmically efficient.
    Units: compressed bytes (len(gzip(cm.tobytes()))).
    """
    if sort_by_degree:
        # Canonical ordering by degree (makes comparison fair)
        degrees = cm.sum(axis=0) + cm.sum(axis=1)
        if tie_breaker == "wl":
            keys = _wl_tiebreak_keys(cm, n_iter=4)
            idx = np.lexsort((keys, -degrees))
        else:
            idx = np.argsort(degrees)[::-1]
        cm = cm[idx][:, idx]

    # Compress
    compressed = gzip.compress(cm.tobytes())
    return float(len(compressed))


def compute_compression_complexity_with_node_features(
    cm: np.ndarray,
    node_features: np.ndarray,
    sort_by_degree: bool = True,
    tie_breaker: str = "index",
) -> float:
    if node_features.ndim == 1:
        node_features = node_features[:, None]
    if node_features.shape[0] != cm.shape[0]:
        raise ValueError(f"node_features has {node_features.shape[0]} rows but cm is {cm.shape[0]}x{cm.shape[0]}")

    if sort_by_degree:
        degrees = cm.sum(axis=0) + cm.sum(axis=1)
        if tie_breaker == "wl":
            keys = _wl_tiebreak_keys(cm, n_iter=4)
            idx = np.lexsort((keys, -degrees))
        else:
            idx = np.argsort(degrees)[::-1]
        cm = cm[idx][:, idx]
        node_features = node_features[idx]

    payload = cm.tobytes() + node_features.astype(np.int16, copy=False).tobytes()
    compressed = gzip.compress(payload)
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

        idx1, idx2 = np.random.choice(n_edges, 2, replace=False)
        u, v = edges[idx1]
        x, y = edges[idx2]

        if u == y or x == v:
            continue
        if cm_rand[u, y] == 1 or cm_rand[x, v] == 1:
            continue

        cm_rand[u, v] = 0
        cm_rand[x, y] = 0
        cm_rand[u, y] = 1
        cm_rand[x, v] = 1

        edges[idx1] = (u, y)
        edges[idx2] = (x, v)
        successful_swaps += 1

    return cm_rand


def randomize_matrix_er(cm: np.ndarray, seed: int = None) -> np.ndarray:
    if seed is not None:
        rng = np.random.default_rng(seed)
    else:
        rng = np.random.default_rng()

    n = cm.shape[0]
    m = int(cm.sum())
    if n <= 1 or m <= 0:
        return np.zeros_like(cm)

    possible = n * (n - 1)
    m = min(m, possible)
    chosen = rng.choice(possible, size=m, replace=False)
    rows = chosen // (n - 1)
    cols = chosen % (n - 1)
    cols = cols + (cols >= rows)

    out = np.zeros((n, n), dtype=int)
    out[rows, cols] = 1
    return out


def extract_gate_features(network_data: dict) -> Optional[np.ndarray]:
    gates = network_data.get("gates")
    if not isinstance(gates, dict) or "nodes" not in network_data:
        return None

    nodes = network_data["nodes"]
    gate_labels: list[str] = []
    input_counts: list[int] = []
    for node in nodes:
        g = gates.get(node, {})
        label = str(g.get("gate", "UNKNOWN"))
        inputs = g.get("inputs", [])
        k = len(inputs) if isinstance(inputs, list) else 0
        gate_labels.append(label)
        input_counts.append(k)

    uniq = sorted(set(gate_labels))
    gate_to_id = {g: i + 1 for i, g in enumerate(uniq)}
    gate_ids = np.array([gate_to_id[g] for g in gate_labels], dtype=int)
    input_counts_arr = np.array(input_counts, dtype=int)
    feats = np.stack([gate_ids, input_counts_arr], axis=1)

    if np.all(feats == 0):
        return None
    return feats


def compute_D_bio_vs_random(
    cm: np.ndarray,
    n_random: int = 100,
    seed_base: int = 42,
    null_model: str = "degree_preserved",
    node_features: Optional[np.ndarray] = None,
    n_swaps: Optional[int] = None,
    sort_by_degree: bool = True,
    tie_breaker: str = "index",
) -> Dict:
    """
    Compute algorithmic complexity D for biological network and random ensemble.

    Returns:
        D_bio: complexity of biological network
        D_random_mean: mean complexity of randomized networks
        D_random_std: std of randomized networks
        z_score: (D_random_mean - D_bio) / D_random_std
        p_value: one-sided test for unusually low D_bio vs random ensemble
    """
    if null_model == "gate_permuted":
        if node_features is None:
            raise ValueError("null_model='gate_permuted' requires node_features")
        D_bio = compute_compression_complexity_with_node_features(
            cm,
            node_features,
            sort_by_degree=sort_by_degree,
            tie_breaker=tie_breaker,
        )
    else:
        D_bio = compute_compression_complexity(cm, sort_by_degree=sort_by_degree, tie_breaker=tie_breaker)

    # Random ensemble
    D_randoms = []
    for i in range(n_random):
        if null_model == "degree_preserved":
            cm_rand = randomize_matrix_deg_preserve(cm, n_swaps=n_swaps, seed=seed_base + i)
            D_rand = compute_compression_complexity(cm_rand, sort_by_degree=sort_by_degree, tie_breaker=tie_breaker)
        elif null_model == "er":
            cm_rand = randomize_matrix_er(cm, seed=seed_base + i)
            D_rand = compute_compression_complexity(cm_rand, sort_by_degree=sort_by_degree, tie_breaker=tie_breaker)
        elif null_model == "gate_permuted":
            rng = np.random.default_rng(seed_base + i)
            perm = rng.permutation(node_features.shape[0])
            D_rand = compute_compression_complexity_with_node_features(
                cm,
                node_features[perm],
                sort_by_degree=sort_by_degree,
                tie_breaker=tie_breaker,
            )
        else:
            raise ValueError(f"Unknown null_model: {null_model}")
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
        "ratio": D_bio / D_random_mean if D_random_mean > 0 else 1.0,
        "null_model": null_model,
    }


# ============================================================================
# SECTION 3: DIFFERENTIAL COMPLEXITY FOR ESSENTIALITY
# ============================================================================

def compute_delta_D(cm: np.ndarray, node_idx: int, n_random: int = 50) -> float:
    """
    Compute differential algorithmic complexity ΔD for a node.

    ΔD = D(network) - D(network without node)

    Positive ΔD means removing the node reduces description length (information loss
    under removal).
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

    delta_D = D_full - D_reduced

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

def _bootstrap_mean_ci(values: np.ndarray, n_boot: int = 5000, seed: int = 42) -> Tuple[float, float, float]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return float("nan"), float("nan"), float("nan")

    rng = np.random.default_rng(seed)
    means = []
    for _ in range(n_boot):
        sample = rng.choice(values, size=values.size, replace=True)
        means.append(float(np.mean(sample)))
    lo, hi = np.quantile(means, [0.025, 0.975])
    return float(np.mean(values)), float(lo), float(hi)


def generate_figure1(results_long: pd.DataFrame, output_dir: str = "../figures"):
    """
    Figure 1: D_bio vs D_random across null families.

    Panels:
    - ER null
    - Degree-preserved null
    - Gate-permuted null (subset with gate annotations)
    - Robustness vs null ensemble size (subsampling from stored null draws)
    """
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    axes = axes.flatten()

    null_order = [
        ("er", "ER null (matched density)"),
        ("degree_preserved", "Degree-preserved null"),
        ("gate_permuted", "Gate-permuted null"),
    ]

    for ax, (null_key, label) in zip(axes[:3], null_order):
        sub = results_long[results_long["null_model"] == null_key].copy()
        if len(sub) == 0:
            ax.set_axis_off()
            continue

        folds = (sub["D_random_mean"].to_numpy(dtype=float) / sub["D_bio"].to_numpy(dtype=float))
        mean_fold, lo, hi = _bootstrap_mean_ci(folds, n_boot=5000, seed=42)

        ax.hist(folds, bins=25, color="#3498db", edgecolor="white", alpha=0.85)
        ax.axvline(1.0, color="red", linestyle="--", lw=1)
        ax.axvline(mean_fold, color="#2ecc71", lw=2)
        ax.set_title(label)
        ax.set_xlabel("Fold reduction (D_null / D_bio)")
        ax.set_ylabel("Number of Networks")
        ax.text(
            0.98,
            0.98,
            f"N={len(folds)}\nmean={mean_fold:.3f}\n95% CI [{lo:.3f},{hi:.3f}]",
            transform=ax.transAxes,
            va="top",
            ha="right",
            fontsize=9,
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
        )

    ax = axes[3]
    ks = [5, 10, 20, 30, 50]
    sub = results_long[results_long["null_model"] == "degree_preserved"].copy()
    sub = sub[sub["D_random_all"].notna()]
    if len(sub) == 0:
        ax.set_axis_off()
    else:
        means = []
        los = []
        his = []
        for k in ks:
            folds_k = []
            for _, row in sub.iterrows():
                draws = row["D_random_all"]
                if not isinstance(draws, list) or len(draws) < k:
                    continue
                Dk = float(np.mean(draws[:k]))
                folds_k.append(Dk / float(row["D_bio"]))
            m, lo, hi = _bootstrap_mean_ci(np.array(folds_k, dtype=float), n_boot=3000, seed=42 + k)
            means.append(m)
            los.append(lo)
            his.append(hi)

        ax.plot(ks, means, "-o", color="#2ecc71", lw=2)
        ax.fill_between(ks, los, his, color="#2ecc71", alpha=0.2)
        ax.axhline(1.0, color="red", linestyle="--", lw=1)
        ax.set_title("Robustness vs null ensemble size (degree-preserved)")
        ax.set_xlabel("Null samples used (k)")
        ax.set_ylabel("Mean fold reduction (D_null / D_bio)")

    plt.tight_layout()
    plt.savefig(f"{output_dir}/figure1_algorithmic_efficiency.pdf")
    plt.savefig(f"{output_dir}/figure1_algorithmic_efficiency.png")
    print(f"Saved Figure 1 to {output_dir}/")
    plt.close()


def generate_figure2(ess_df: pd.DataFrame, networks: Dict[str, dict], output_dir: str = "../figures"):
    df = ess_df.copy()
    df = _annotate_essentiality(df, networks)

    required = ["Essentiality", "Delta_D", "Degree", "Betweenness"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Essentiality dataset missing required columns: {missing}")

    df = df.dropna(subset=["Essentiality", "Delta_D", "Degree", "Betweenness"]).copy()
    y = df["Essentiality"].astype(int).to_numpy()
    groups = df["Network"].astype(str).to_numpy()

    scores = {
        "ΔD": df["Delta_D"].astype(float).to_numpy(),
        "Degree": df["Degree"].astype(float).to_numpy(),
        "Betweenness": df["Betweenness"].astype(float).to_numpy(),
    }

    uniq_groups = np.unique(groups)
    n_splits = int(min(5, max(2, len(uniq_groups))))
    splits = _group_stratified_folds(groups, y, n_splits=n_splits, seed=42)

    X = df[["Delta_D", "Degree", "Betweenness"]].to_numpy(dtype=float)
    oof = np.full(len(df), np.nan, dtype=float)
    used_folds = 0
    skipped_folds = 0
    for train_idx, test_idx in splits:
        y_train = y[train_idx]
        y_test = y[test_idx]
        if len(np.unique(y_train)) < 2 or len(np.unique(y_test)) < 2:
            skipped_folds += 1
            continue
        X_train = X[train_idx]
        X_test = X[test_idx]

        mean = X_train.mean(axis=0, keepdims=True)
        std = X_train.std(axis=0, keepdims=True) + 1e-8
        X_train = (X_train - mean) / std
        X_test = (X_test - mean) / std

        clf = LogisticRegression(random_state=42, max_iter=2000, class_weight="balanced")
        clf.fit(X_train, y_train)
        oof[test_idx] = clf.predict_proba(X_test)[:, 1]
        used_folds += 1

    valid_oof = np.isfinite(oof)
    if not np.any(valid_oof):
        raise RuntimeError("Combined model produced no valid out-of-fold predictions.")

    scores["Combined"] = oof

    colors = {
        "ΔD": "#2ecc71",
        "Degree": "#3498db",
        "Betweenness": "#e74c3c",
        "Combined": "#9b59b6",
    }

    rng_seed = 42
    n_boot = 5000
    summary_rows = []
    boot_store = {}
    for name, s in scores.items():
        auc_m, auc_lo, auc_hi, auc_boot = _bootstrap_grouped_metric(
            y[valid_oof] if name == "Combined" else y,
            s[valid_oof] if name == "Combined" else s,
            groups[valid_oof] if name == "Combined" else groups,
            n_boot=n_boot,
            seed=rng_seed,
            metric="auc",
        )
        ap_m, ap_lo, ap_hi, ap_boot = _bootstrap_grouped_metric(
            y[valid_oof] if name == "Combined" else y,
            s[valid_oof] if name == "Combined" else s,
            groups[valid_oof] if name == "Combined" else groups,
            n_boot=n_boot,
            seed=rng_seed + 1,
            metric="ap",
        )
        summary_rows.append(
            {
                "Metric": name,
                "AUC": auc_m,
                "AUC_CI95": [auc_lo, auc_hi],
                "AP": ap_m,
                "AP_CI95": [ap_lo, ap_hi],
            }
        )
        boot_store[name] = {"auc": auc_boot, "ap": ap_boot}

    comparisons = []

    for a, b in [("ΔD", "Degree"), ("ΔD", "Betweenness")]:
        da = boot_store[a]["auc"]
        db = boot_store[b]["auc"]
        n = min(len(da), len(db))
        comparisons.append(
            {
                "contrast": f"{a} - {b}",
                "metric": "AUC",
                "p_value": _paired_bootstrap_pvalue(da[:n] - db[:n]) if n else float("nan"),
            }
        )

    dd_oof_base, _, _, dd_oof_boot = _bootstrap_grouped_metric(
        y[valid_oof],
        scores["ΔD"][valid_oof],
        groups[valid_oof],
        n_boot=n_boot,
        seed=rng_seed,
        metric="auc",
    )
    comb_boot = boot_store["Combined"]["auc"]
    n = min(len(comb_boot), len(dd_oof_boot))
    comparisons.append(
        {
            "contrast": "Combined - ΔD",
            "metric": "AUC",
            "p_value": _paired_bootstrap_pvalue(comb_boot[:n] - dd_oof_boot[:n]) if n else float("nan"),
            "note": f"ΔD baseline on Combined OOF subset: AUC={dd_oof_base:.3f}",
        }
    )

    delta_auc = float(roc_auc_score(y, scores["ΔD"]))
    delta_auc_neg = float(roc_auc_score(y, -scores["ΔD"]))
    sign_check = {"AUC(ΔD)": delta_auc, "AUC(-ΔD)": delta_auc_neg}

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))

    ax = axes[0]
    for name, s in scores.items():
        ys = y[valid_oof] if name == "Combined" else y
        ss = s[valid_oof] if name == "Combined" else s
        fpr, tpr, _ = roc_curve(ys, ss)
        row = next(r for r in summary_rows if r["Metric"] == name)
        ax.plot(
            fpr,
            tpr,
            label=f"{name} AUC={row['AUC']:.3f} [{row['AUC_CI95'][0]:.3f},{row['AUC_CI95'][1]:.3f}]",
            color=colors[name],
            lw=2,
        )
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("Essentiality prediction (ROC)")
    ax.legend(loc="lower right", fontsize=8)

    ax = axes[1]
    for name, s in scores.items():
        ys = y[valid_oof] if name == "Combined" else y
        ss = s[valid_oof] if name == "Combined" else s
        p, r, _ = precision_recall_curve(ys, ss)
        row = next(r0 for r0 in summary_rows if r0["Metric"] == name)
        ax.plot(
            r,
            p,
            label=f"{name} AP={row['AP']:.3f} [{row['AP_CI95'][0]:.3f},{row['AP_CI95'][1]:.3f}]",
            color=colors[name],
            lw=2,
        )
    base = float(np.mean(y))
    ax.axhline(base, color="k", linestyle="--", alpha=0.4, lw=1)
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Essentiality prediction (PR)")
    ax.legend(loc="lower left", fontsize=8)

    plt.tight_layout()
    plt.savefig(f"{output_dir}/figure2_essentiality_prediction.pdf")
    plt.savefig(f"{output_dir}/figure2_essentiality_prediction.png")
    plt.close()
    print(f"Saved Figure 2 to {output_dir}/")

    summary = {
        "n_rows": int(len(df)),
        "n_networks": int(df["Network"].nunique()),
        "prevalence": float(np.mean(y)),
        "combined_model_folds_used": int(used_folds),
        "combined_model_folds_skipped": int(skipped_folds),
        "bootstrap": {"n_boot": int(n_boot), "seed": int(rng_seed), "resample_unit": "network"},
        "metrics": summary_rows,
        "comparisons": comparisons,
        "delta_D_sign_check": sign_check,
    }

    out_dir = Path(output_dir)
    with open(out_dir / "essentiality_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    strat_rows = []
    for strat_name in ["Organism_Group", "Size_Bin", "Source"]:
        for level, sub in df.groupby(strat_name):
            ys = sub["Essentiality"].astype(int).to_numpy()
            gs = sub["Network"].astype(str).to_numpy()
            if len(np.unique(ys)) < 2 or len(np.unique(gs)) < 2:
                continue
            for metric_name in ["ΔD", "Degree", "Betweenness"]:
                ss = sub[{"ΔD": "Delta_D", "Degree": "Degree", "Betweenness": "Betweenness"}[metric_name]].to_numpy(dtype=float)
                auc_m, auc_lo, auc_hi, _ = _bootstrap_grouped_metric(
                    ys,
                    ss,
                    gs,
                    n_boot=2000,
                    seed=42,
                    metric="auc",
                )
                ap_m, ap_lo, ap_hi, _ = _bootstrap_grouped_metric(
                    ys,
                    ss,
                    gs,
                    n_boot=2000,
                    seed=43,
                    metric="ap",
                )
                strat_rows.append(
                    {
                        "Stratum": strat_name,
                        "Level": str(level),
                        "Metric": metric_name,
                        "n_rows": int(len(sub)),
                        "n_networks": int(len(np.unique(gs))),
                        "prevalence": float(np.mean(ys)),
                        "AUC": auc_m,
                        "AUC_CI95_lo": auc_lo,
                        "AUC_CI95_hi": auc_hi,
                        "AP": ap_m,
                        "AP_CI95_lo": ap_lo,
                        "AP_CI95_hi": ap_hi,
                    }
                )
    if strat_rows:
        pd.DataFrame(strat_rows).to_csv(out_dir / "essentiality_stratified.csv", index=False)


def generate_figure2_baseline_benchmarks(ess_df: pd.DataFrame, networks: Dict[str, dict], output_dir: str = "../figures"):
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = ess_df.copy()
    df = _annotate_essentiality(df, networks)

    base_required = ["Essentiality", "Delta_D", "Degree", "Betweenness"]
    missing = [c for c in base_required if c not in df.columns]
    if missing:
        raise ValueError(f"Essentiality dataset missing required columns: {missing}")

    baselines = []
    for net_name, net_data in networks.items():
        b = _node_baselines(net_data)
        b["Network"] = str(net_name)
        baselines.append(b)
    if baselines:
        base_df = pd.concat(baselines, ignore_index=True)
        df = df.merge(base_df, on=["Network", "Gene"], how="left")

    depmap_feats = _depmap_gene_feature_means(df["Gene"].astype(str).unique().tolist())
    df = df.merge(depmap_feats, on="Gene", how="left")

    gnomad_feats = _gnomad_constraint_features(df["Gene"].astype(str).unique().tolist())
    df = df.merge(gnomad_feats, on="Gene", how="left")

    df = df.dropna(subset=["Essentiality", "Delta_D", "Degree", "Betweenness"]).copy()

    def _oof_predict_proba(
        X: np.ndarray,
        y: np.ndarray,
        groups: np.ndarray,
        model_kind: str,
        seed: int,
        n_splits: int = 5,
    ) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=int)
        groups = np.asarray(groups, dtype=str)
        n = X.shape[0]
        oof = np.full(n, np.nan, dtype=float)

        splits = _group_stratified_folds(groups, y, n_splits=n_splits, seed=seed)
        for train_idx, test_idx in splits:
            Xtr = X[train_idx].copy()
            Xte = X[test_idx].copy()
            ytr = y[train_idx]
            if len(np.unique(ytr)) < 2:
                oof[test_idx] = float(np.mean(ytr))
                continue

            col_means = np.nanmean(Xtr, axis=0)
            col_means = np.where(np.isfinite(col_means), col_means, 0.0)
            Xtr = np.where(np.isfinite(Xtr), Xtr, col_means)
            Xte = np.where(np.isfinite(Xte), Xte, col_means)

            mu = Xtr.mean(axis=0)
            sd = Xtr.std(axis=0)
            sd = np.where(sd > 0, sd, 1.0)
            Xtr = (Xtr - mu) / sd
            Xte = (Xte - mu) / sd

            if model_kind == "logreg":
                model = LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    solver="lbfgs",
                )
            elif model_kind == "rf":
                model = RandomForestClassifier(
                    n_estimators=500,
                    random_state=seed,
                    class_weight="balanced_subsample",
                    min_samples_leaf=5,
                    n_jobs=-1,
                )
            else:
                raise ValueError(f"Unknown model_kind: {model_kind}")

            model.fit(Xtr, ytr)
            oof[test_idx] = model.predict_proba(Xte)[:, 1]

        return oof

    feature_sets = {
        "dd": ["Delta_D"],
        "graph": ["Degree", "Betweenness", "Closeness", "Eigenvector"],
        "dd_graph": ["Delta_D", "Degree", "Betweenness", "Closeness", "Eigenvector"],
        "depmap": ["DepMapExpr_mean", "DepMapCN_mean"],
        "graph_depmap": ["Degree", "Betweenness", "Closeness", "Eigenvector", "DepMapExpr_mean", "DepMapCN_mean"],
        "dd_all": ["Delta_D", "Degree", "Betweenness", "Closeness", "Eigenvector", "DepMapExpr_mean", "DepMapCN_mean"],
        "gnomad": ["gnomAD_pLI", "gnomAD_LOEUF"],
        "graph_gnomad": ["Degree", "Betweenness", "Closeness", "Eigenvector", "gnomAD_pLI", "gnomAD_LOEUF"],
        "dd_graph_gnomad": ["Delta_D", "Degree", "Betweenness", "Closeness", "Eigenvector", "gnomAD_pLI", "gnomAD_LOEUF"],
    }

    def _eval_suite(df_suite: pd.DataFrame, suite_name: str, include_depmap: bool, include_gnomad: bool) -> dict:
        if len(df_suite) == 0:
            oof_path = out_dir / f"essentiality_benchmark_oof_{suite_name}.csv"
            pd.DataFrame({"Gene": [], "Network": [], "Essentiality": []}).to_csv(oof_path, index=False)
            return {"suite": suite_name, "n_rows": 0, "n_networks": 0, "models": {}}

        y = df_suite["Essentiality"].astype(int).to_numpy()
        groups = df_suite["Network"].astype(str).to_numpy()

        models = []
        models.append(("ΔD", "logreg", "dd"))
        models.append(("Graph", "logreg", "graph"))
        models.append(("ΔD+Graph", "logreg", "dd_graph"))
        if include_depmap:
            models.append(("DepMap", "logreg", "depmap"))
            models.append(("Graph+DepMap", "logreg", "graph_depmap"))
            models.append(("ΔD+Graph+DepMap", "logreg", "dd_all"))
            models.append(("RF (all)", "rf", "dd_all"))
        if include_gnomad:
            models.append(("Constraint", "logreg", "gnomad"))
            models.append(("Graph+Constraint", "logreg", "graph_gnomad"))
            models.append(("ΔD+Graph+Constraint", "logreg", "dd_graph_gnomad"))
            models.append(("RF (constraint)", "rf", "dd_graph_gnomad"))

        results = {"suite": suite_name, "n_rows": int(len(df_suite)), "n_networks": int(df_suite["Network"].nunique()), "models": {}}

        oof_tbl = df_suite[["Gene", "Network"]].copy()
        oof_tbl["Essentiality"] = y

        for model_name, model_kind, feat_key in models:
            feats = [c for c in feature_sets[feat_key] if c in df_suite.columns]
            if len(feats) == 0:
                continue
            X = df_suite[feats].to_numpy(dtype=float)
            prob = _oof_predict_proba(X, y, groups, model_kind=model_kind, seed=41, n_splits=5)
            oof_tbl[model_name] = prob

            auc, auc_lo, auc_hi, auc_boot = _bootstrap_grouped_metric(
                y, prob, groups, n_boot=2000, seed=42, metric="auc"
            )
            ap, ap_lo, ap_hi, ap_boot = _bootstrap_grouped_metric(
                y, prob, groups, n_boot=2000, seed=43, metric="ap"
            )
            brier, brier_lo, brier_hi, brier_boot = _bootstrap_grouped_brier(
                y, prob, groups, n_boot=2000, seed=44
            )
            cal = _calibration_bins(prob, y, n_bins=10)

            results["models"][model_name] = {
                "features": feats,
                "auc": auc,
                "auc_ci95": [auc_lo, auc_hi],
                "ap": ap,
                "ap_ci95": [ap_lo, ap_hi],
                "brier": brier,
                "brier_ci95": [brier_lo, brier_hi],
                "calibration": cal,
            }

            results["models"][model_name]["_boot"] = {
                "auc": auc_boot.tolist() if isinstance(auc_boot, np.ndarray) else [],
                "ap": ap_boot.tolist() if isinstance(ap_boot, np.ndarray) else [],
                "brier": brier_boot.tolist() if isinstance(brier_boot, np.ndarray) else [],
            }

        if "ΔD" in results["models"] and "Graph" in results["models"]:
            d = np.array(results["models"]["ΔD"]["_boot"]["auc"], dtype=float) - np.array(
                results["models"]["Graph"]["_boot"]["auc"], dtype=float
            )
            d = d[np.isfinite(d)]
            if d.size:
                results["comparisons"] = {
                    "ΔAUC(ΔD-Graph)": {
                        "mean": float(np.mean(d)),
                        "ci95": [float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))],
                        "p_value_two_sided": _paired_bootstrap_pvalue(d),
                    }
                }

        if include_depmap and "ΔD+Graph+DepMap" in results["models"] and "Graph+DepMap" in results["models"]:
            d = np.array(results["models"]["ΔD+Graph+DepMap"]["_boot"]["auc"], dtype=float) - np.array(
                results["models"]["Graph+DepMap"]["_boot"]["auc"], dtype=float
            )
            d = d[np.isfinite(d)]
            if d.size:
                if "comparisons" not in results:
                    results["comparisons"] = {}
                results["comparisons"]["ΔAUC(ΔD+Graph+DepMap - Graph+DepMap)"] = {
                    "mean": float(np.mean(d)),
                    "ci95": [float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))],
                    "p_value_two_sided": _paired_bootstrap_pvalue(d),
                    "passes_gate_c_min_delta_auc_0_05": bool(float(np.mean(d)) >= 0.05),
                }

        if include_gnomad and "ΔD+Graph+Constraint" in results["models"] and "Graph+Constraint" in results["models"]:
            d = np.array(results["models"]["ΔD+Graph+Constraint"]["_boot"]["auc"], dtype=float) - np.array(
                results["models"]["Graph+Constraint"]["_boot"]["auc"], dtype=float
            )
            d = d[np.isfinite(d)]
            if d.size:
                if "comparisons" not in results:
                    results["comparisons"] = {}
                results["comparisons"]["ΔAUC(ΔD+Graph+Constraint - Graph+Constraint)"] = {
                    "mean": float(np.mean(d)),
                    "ci95": [float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))],
                    "p_value_two_sided": _paired_bootstrap_pvalue(d),
                    "passes_gate_c_min_delta_auc_0_05": bool(float(np.mean(d)) >= 0.05),
                }

        for k in list(results["models"].keys()):
            if "_boot" in results["models"][k]:
                del results["models"][k]["_boot"]

        oof_path = out_dir / f"essentiality_benchmark_oof_{suite_name}.csv"
        oof_tbl.to_csv(oof_path, index=False)
        return results

    full_mask = (
        df[["Delta_D", "Degree", "Betweenness"]].notna().all(axis=1)
        & df["Essentiality"].notna()
    )
    df_full = df.loc[full_mask].copy()
    suite_full = _eval_suite(df_full, "full", include_depmap=False, include_gnomad=False)

    depmap_cols = ["DepMapExpr_mean", "DepMapCN_mean"]
    depmap_mask = full_mask.copy()
    for c in depmap_cols:
        if c in df.columns:
            depmap_mask &= df[c].notna()
        else:
            depmap_mask &= False
    df_depmap = df.loc[depmap_mask].copy()
    suite_depmap = _eval_suite(df_depmap, "depmap", include_depmap=(len(df_depmap) > 0), include_gnomad=False)

    gnomad_cols = ["gnomAD_pLI", "gnomAD_LOEUF"]
    gnomad_mask = full_mask.copy()
    for c in gnomad_cols:
        if c in df.columns:
            gnomad_mask &= df[c].notna()
        else:
            gnomad_mask &= False
    df_gnomad = df.loc[gnomad_mask].copy()
    suite_gnomad = _eval_suite(df_gnomad, "gnomad", include_depmap=False, include_gnomad=(len(df_gnomad) > 0))

    with open(out_dir / "essentiality_benchmark_summary.json", "w") as f:
        json.dump(
            {
                "protocol": {
                    "split": "group_stratified_kfold_by_network",
                    "n_splits": 5,
                    "bootstrap": {"n_boot": 2000, "group_unit": "Network"},
                    "calibration_bins": 10,
                },
                "suites": {"full": suite_full, "depmap": suite_depmap, "gnomad": suite_gnomad},
            },
            f,
            indent=2,
        )

    def _plot_suite(df_suite: pd.DataFrame, suite: dict, fname_prefix: str):
        if len(df_suite) == 0 or not suite.get("models"):
            return
        oof_df = pd.read_csv(out_dir / f"essentiality_benchmark_oof_{fname_prefix}.csv")
        y = oof_df["Essentiality"].astype(int).to_numpy()
        fig, axes = plt.subplots(1, 3, figsize=(13.8, 4.3))
        ax_roc, ax_pr, ax_cal = axes

        diag = np.linspace(0, 1, 200)
        ax_roc.plot(diag, diag, linestyle="--", color="gray", linewidth=1.0)
        ax_cal.plot(diag, diag, linestyle="--", color="gray", linewidth=1.0)

        model_order = [
            "ΔD",
            "Graph",
            "ΔD+Graph",
            "Constraint",
            "Graph+Constraint",
            "ΔD+Graph+Constraint",
            "DepMap",
            "Graph+DepMap",
            "ΔD+Graph+DepMap",
            "RF (all)",
            "RF (constraint)",
        ]
        for name in model_order:
            if name not in suite["models"]:
                continue
            prob = oof_df[name].to_numpy(dtype=float)
            mask = np.isfinite(prob)
            if mask.sum() == 0:
                continue

            fpr, tpr, _ = roc_curve(y[mask], prob[mask])
            prec, rec, _ = precision_recall_curve(y[mask], prob[mask])
            ax_roc.plot(fpr, tpr, label=f"{name} (AUC={suite['models'][name]['auc']:.3f})")
            ax_pr.plot(rec, prec, label=f"{name} (AP={suite['models'][name]['ap']:.3f})")

            cal = suite["models"][name]["calibration"]
            mp = np.array(cal["mean_pred"], dtype=float)
            fp = np.array(cal["frac_pos"], dtype=float)
            ok = np.isfinite(mp) & np.isfinite(fp)
            if ok.sum():
                ax_cal.plot(mp[ok], fp[ok], marker="o", linewidth=1.2, label=name)

        ax_roc.set_xlabel("False Positive Rate")
        ax_roc.set_ylabel("True Positive Rate")
        ax_roc.set_title(f"ROC ({fname_prefix})")
        ax_roc.legend(fontsize=8)

        ax_pr.set_xlabel("Recall")
        ax_pr.set_ylabel("Precision")
        ax_pr.set_title(f"Precision-Recall ({fname_prefix})")
        ax_pr.legend(fontsize=8)

        ax_cal.set_xlabel("Mean Predicted Probability")
        ax_cal.set_ylabel("Fraction Positive")
        ax_cal.set_title(f"Calibration ({fname_prefix})")
        ax_cal.legend(fontsize=8)

        plt.tight_layout()
        fig.savefig(out_dir / f"figure2_essentiality_benchmarks_{fname_prefix}.png", dpi=300, bbox_inches="tight")
        fig.savefig(out_dir / f"figure2_essentiality_benchmarks_{fname_prefix}.pdf", bbox_inches="tight")
        plt.close(fig)

    _plot_suite(df_full, suite_full, "full")
    _plot_suite(df_depmap, suite_depmap, "depmap")
    _plot_suite(df_gnomad, suite_gnomad, "gnomad")


def run_reproducibility_stress_tests(output_dir: Optional[str] = None, n_networks: int = 30) -> dict:
    out_dir = Path(output_dir) if output_dir is not None else _paper_figures_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    networks = load_all_networks()

    eligible: list[str] = []
    for name, data in networks.items():
        cm = get_adjacency_matrix(data)
        if 5 <= cm.shape[0] <= 100 and int(cm.sum()) > 0:
            eligible.append(name)
    eligible = sorted(eligible)
    chosen = eligible[: max(0, min(int(n_networks), len(eligible)))]

    def _per_network_null(
        seed_base: int,
        n_random: int,
        n_swaps_mult: Optional[int],
        sort_by_degree: bool,
        tie_breaker: str = "index",
        cm_override: Optional[np.ndarray] = None,
        net_name: Optional[str] = None,
        net_data: Optional[dict] = None,
    ) -> dict:
        if cm_override is not None:
            cm = cm_override
            n_nodes = int(cm.shape[0])
        else:
            assert net_data is not None
            cm = get_adjacency_matrix(net_data)
            n_nodes = int(cm.shape[0])

        n_swaps = None if n_swaps_mult is None else int(n_nodes) * int(n_swaps_mult)
        res = compute_D_bio_vs_random(
            cm,
            n_random=int(n_random),
            seed_base=int(seed_base),
            null_model="degree_preserved",
            n_swaps=n_swaps,
            sort_by_degree=bool(sort_by_degree),
            tie_breaker=str(tie_breaker),
        )
        fold = float(res["D_random_mean"] / res["D_bio"]) if float(res["D_bio"]) > 0 else float("nan")
        return {
            "Network": str(net_name) if net_name is not None else "unknown",
            "n_nodes": int(n_nodes),
            "n_edges": int(cm.sum()),
            "seed_base": int(seed_base),
            "n_random": int(n_random),
            "n_swaps_mult": None if n_swaps_mult is None else int(n_swaps_mult),
            "sort_by_degree": bool(sort_by_degree),
            "tie_breaker": str(tie_breaker),
            "D_bio": float(res["D_bio"]),
            "D_random_mean": float(res["D_random_mean"]),
            "z_score": float(res["z_score"]),
            "p_value": float(res["p_value"]),
            "fold_reduction": fold,
        }

    def _meta_stats(rows: list[dict]) -> dict:
        z = np.array([r["z_score"] for r in rows], dtype=float)
        fold = np.array([r["fold_reduction"] for r in rows], dtype=float)
        p = np.array([r["p_value"] for r in rows], dtype=float)
        return {
            "n_networks": int(len(rows)),
            "mean_z": float(np.nanmean(z)) if len(rows) else float("nan"),
            "median_z": float(np.nanmedian(z)) if len(rows) else float("nan"),
            "mean_fold_reduction": float(np.nanmean(fold)) if len(rows) else float("nan"),
            "fraction_p_le_0_05": float(np.nanmean(p <= 0.05)) if len(rows) else float("nan"),
        }

    tolerances = {
        "null_seed_spearman_min": 0.90,
        "null_seed_abs_mean_z_max": 0.15,
        "null_seed_sign_agreement_min": 0.90,
        "null_n_random_abs_mean_z_max": 0.25,
        "null_n_random_rel_mean_fold_max": 0.08,
        "null_swap_abs_mean_z_max": 0.25,
        "null_swap_rel_mean_fold_max": 0.08,
        "ordering_mean_rel_sd_max": 0.002,
        "ordering_max_rel_sd_max": 0.02,
        "essentiality_auc_range_max": 0.03,
    }

    grid_rows: list[dict] = []

    baseline_seed = 42
    baseline_n_random = 50
    baseline_swaps_mult = 20
    baseline_sort = True

    baseline_rows = []
    for name in chosen:
        baseline_rows.append(
            _per_network_null(
                seed_base=baseline_seed,
                n_random=baseline_n_random,
                n_swaps_mult=baseline_swaps_mult,
                sort_by_degree=baseline_sort,
                net_name=name,
                net_data=networks[name],
            )
        )
    baseline_meta = _meta_stats(baseline_rows)
    for r in baseline_rows:
        rr = dict(r)
        rr["axis"] = "baseline"
        grid_rows.append(rr)

    seed_axes = []
    seed_list = [42, 314159, 271828]
    z_base = np.array([r["z_score"] for r in baseline_rows], dtype=float)
    fold_base = np.array([r["fold_reduction"] for r in baseline_rows], dtype=float)
    for seed in seed_list:
        rows = []
        for name in chosen:
            rows.append(
                _per_network_null(
                    seed_base=seed,
                    n_random=baseline_n_random,
                    n_swaps_mult=baseline_swaps_mult,
                    sort_by_degree=baseline_sort,
                    net_name=name,
                    net_data=networks[name],
                )
            )
        for r in rows:
            rr = dict(r)
            rr["axis"] = "seed"
            grid_rows.append(rr)
        z = np.array([r["z_score"] for r in rows], dtype=float)
        fold = np.array([r["fold_reduction"] for r in rows], dtype=float)
        rho_z = float(stats.spearmanr(z_base, z).correlation) if len(z) >= 5 else float("nan")
        rho_fold = float(stats.spearmanr(fold_base, fold).correlation) if len(fold) >= 5 else float("nan")
        mean_z_diff = float(np.nanmean(z) - np.nanmean(z_base)) if len(z) else float("nan")
        sign_agree = float(np.nanmean(np.sign(z) == np.sign(z_base))) if len(z) else float("nan")
        seed_axes.append(
            {
                "seed_base": int(seed),
                "spearman_z": rho_z,
                "spearman_fold": rho_fold,
                "delta_mean_z": mean_z_diff,
                "sign_agreement": sign_agree,
                "pass": bool(
                    (rho_z >= tolerances["null_seed_spearman_min"])
                    and (abs(mean_z_diff) <= tolerances["null_seed_abs_mean_z_max"])
                    and (sign_agree >= tolerances["null_seed_sign_agreement_min"])
                ),
            }
        )

    n_random_axes = []
    for n_random in [10, 25, 50]:
        rows = []
        for name in chosen:
            rows.append(
                _per_network_null(
                    seed_base=baseline_seed,
                    n_random=n_random,
                    n_swaps_mult=baseline_swaps_mult,
                    sort_by_degree=baseline_sort,
                    net_name=name,
                    net_data=networks[name],
                )
            )
        for r in rows:
            rr = dict(r)
            rr["axis"] = "n_random"
            grid_rows.append(rr)
        meta = _meta_stats(rows)
        abs_mean_z = abs(meta["mean_z"] - baseline_meta["mean_z"])
        denom = float(baseline_meta["mean_fold_reduction"])
        rel_fold = float("nan") if (not np.isfinite(denom) or denom == 0.0) else abs(meta["mean_fold_reduction"] - denom) / abs(denom)
        required = bool(int(n_random) >= 25)
        passed = bool(
            (abs_mean_z <= tolerances["null_n_random_abs_mean_z_max"])
            and (rel_fold <= tolerances["null_n_random_rel_mean_fold_max"])
        )
        n_random_axes.append(
            {
                "n_random": int(n_random),
                "meta": meta,
                "abs_delta_mean_z": float(abs_mean_z),
                "rel_delta_mean_fold": float(rel_fold),
                "required": required,
                "pass": passed,
            }
        )

    swap_axes = []
    for mult in [5, 20, 100]:
        rows = []
        for name in chosen:
            rows.append(
                _per_network_null(
                    seed_base=baseline_seed,
                    n_random=baseline_n_random,
                    n_swaps_mult=mult,
                    sort_by_degree=baseline_sort,
                    net_name=name,
                    net_data=networks[name],
                )
            )
        for r in rows:
            rr = dict(r)
            rr["axis"] = "n_swaps"
            grid_rows.append(rr)
        meta = _meta_stats(rows)
        abs_mean_z = abs(meta["mean_z"] - baseline_meta["mean_z"])
        denom = float(baseline_meta["mean_fold_reduction"])
        rel_fold = float("nan") if (not np.isfinite(denom) or denom == 0.0) else abs(meta["mean_fold_reduction"] - denom) / abs(denom)
        swap_axes.append(
            {
                "n_swaps_mult": int(mult),
                "meta": meta,
                "abs_delta_mean_z": float(abs_mean_z),
                "rel_delta_mean_fold": float(rel_fold),
                "pass": bool(
                    (abs_mean_z <= tolerances["null_swap_abs_mean_z_max"])
                    and (rel_fold <= tolerances["null_swap_rel_mean_fold_max"])
                ),
            }
        )

    ordering_rows = []
    n_perm = 10
    n_perm_control = 10
    rng_ctrl = np.random.default_rng(123)
    for name in chosen:
        cm0 = get_adjacency_matrix(networks[name])
        D_false = []
        for _ in range(n_perm_control):
            perm = rng_ctrl.permutation(cm0.shape[0])
            cm = cm0[perm][:, perm]
            D_false.append(compute_compression_complexity(cm, sort_by_degree=False))
        D_false = np.asarray(D_false, dtype=float)
        mean_false = float(np.mean(D_false)) if D_false.size else float("nan")
        rel_range_false = float((np.max(D_false) - np.min(D_false)) / mean_false) if (D_false.size and np.isfinite(mean_false) and mean_false) else float("nan")
        ordering_rows.append(
            {
                "Network": str(name),
                "tie_breaker": "none",
                "mean_D_sort_by_degree_true": float("nan"),
                "rel_sd_D_sort_by_degree_true": float("nan"),
                "rel_range_D_sort_by_degree_true": float("nan"),
                "rel_range_D_sort_by_degree_false": rel_range_false,
            }
        )

    for tie in ["index", "wl"]:
        rng = np.random.default_rng(123)
        for name in chosen:
            cm0 = get_adjacency_matrix(networks[name])
            Ds = []
            for _ in range(n_perm):
                perm = rng.permutation(cm0.shape[0])
                cm = cm0[perm][:, perm]
                Ds.append(compute_compression_complexity(cm, sort_by_degree=True, tie_breaker=tie))
            Ds = np.asarray(Ds, dtype=float)
            mean_D = float(np.mean(Ds)) if Ds.size else float("nan")
            sd_D = float(np.std(Ds, ddof=1)) if Ds.size > 1 else float("nan")
            rel_sd = float(sd_D / mean_D) if (np.isfinite(mean_D) and mean_D) else float("nan")
            rel_range = float((np.max(Ds) - np.min(Ds)) / mean_D) if (Ds.size and np.isfinite(mean_D) and mean_D) else float("nan")
            ordering_rows.append(
                {
                    "Network": str(name),
                    "tie_breaker": str(tie),
                    "mean_D_sort_by_degree_true": mean_D,
                    "rel_sd_D_sort_by_degree_true": rel_sd,
                    "rel_range_D_sort_by_degree_true": rel_range,
                    "rel_range_D_sort_by_degree_false": float("nan"),
                }
            )

    ordering_df = pd.DataFrame(ordering_rows)
    def _summ_for_tie(tie: str) -> dict:
        sub = ordering_df[ordering_df["tie_breaker"] == tie]
        return {
            "mean_rel_sd_D": float(sub["rel_sd_D_sort_by_degree_true"].mean()) if len(sub) else float("nan"),
            "max_rel_sd_D": float(sub["rel_sd_D_sort_by_degree_true"].max()) if len(sub) else float("nan"),
            "mean_rel_range_D": float(sub["rel_range_D_sort_by_degree_true"].mean()) if len(sub) else float("nan"),
            "pass": bool(
                (len(sub) > 0)
                and (float(sub["rel_sd_D_sort_by_degree_true"].mean()) <= tolerances["ordering_mean_rel_sd_max"])
                and (float(sub["rel_sd_D_sort_by_degree_true"].max()) <= tolerances["ordering_max_rel_sd_max"])
            ),
        }

    ordering_summary = {
        "control_sort_by_degree_false": {
            "mean_rel_range_D": float(ordering_df.loc[ordering_df["tie_breaker"] == "none", "rel_range_D_sort_by_degree_false"].mean())
            if (ordering_df["tie_breaker"] == "none").any()
            else float("nan"),
            "n_permutations_control": int(n_perm_control),
        },
        "tie_breaker_index": _summ_for_tie("index"),
        "tie_breaker_wl": _summ_for_tie("wl"),
        "pass": bool(_summ_for_tie("wl")["pass"]),
    }

    for r in ordering_rows:
        grid_rows.append({"axis": "ordering", **r})

    ess = load_essentiality_data()
    ess = _annotate_essentiality(ess, networks)

    baselines = []
    for net_name, net_data in networks.items():
        b = _node_baselines(net_data)
        b["Network"] = str(net_name)
        baselines.append(b)
    if baselines:
        base_df = pd.concat(baselines, ignore_index=True)
        ess = ess.merge(base_df, on=["Network", "Gene"], how="left")

    gnomad_feats = _gnomad_constraint_features(ess["Gene"].astype(str).unique().tolist())
    ess = ess.merge(gnomad_feats, on="Gene", how="left")

    def _oof_auc_for_seed(df: pd.DataFrame, features: list[str], seed: int) -> dict:
        df = df.dropna(subset=["Essentiality"] + features).copy()
        if len(df) == 0:
            return {"n_rows": 0, "n_networks": 0, "auc": float("nan"), "ap": float("nan"), "brier": float("nan")}

        y = df["Essentiality"].astype(int).to_numpy()
        groups = df["Network"].astype(str).to_numpy()
        X = df[features].to_numpy(dtype=float)

        prob = np.full(len(df), np.nan, dtype=float)
        splits = _group_stratified_folds(groups, y, n_splits=5, seed=seed)
        for tr, te in splits:
            Xtr = X[tr].copy()
            Xte = X[te].copy()
            ytr = y[tr]
            if len(np.unique(ytr)) < 2:
                prob[te] = float(np.mean(ytr))
                continue

            mu = Xtr.mean(axis=0)
            sd = Xtr.std(axis=0)
            sd = np.where(sd > 0, sd, 1.0)
            Xtr = (Xtr - mu) / sd
            Xte = (Xte - mu) / sd

            model = LogisticRegression(max_iter=2000, class_weight="balanced", solver="lbfgs")
            model.fit(Xtr, ytr)
            prob[te] = model.predict_proba(Xte)[:, 1]

        mask = np.isfinite(prob)
        if mask.sum() == 0 or len(np.unique(y[mask])) < 2:
            return {"n_rows": int(len(df)), "n_networks": int(df["Network"].nunique()), "auc": float("nan"), "ap": float("nan"), "brier": float("nan")}

        auc = float(roc_auc_score(y[mask], prob[mask]))
        ap = float(average_precision_score(y[mask], prob[mask]))
        brier = float(brier_score_loss(y[mask], prob[mask]))
        return {"n_rows": int(len(df)), "n_networks": int(df["Network"].nunique()), "auc": auc, "ap": ap, "brier": brier}

    essentiality_seed_axes = []
    seed_list = [1, 2, 3, 4, 5]
    tasks = [
        ("ΔD", ["Delta_D"], ess),
        ("Graph", ["Degree", "Betweenness", "Closeness", "Eigenvector"], ess),
        ("ΔD+Graph", ["Delta_D", "Degree", "Betweenness", "Closeness", "Eigenvector"], ess),
        ("Constraint", ["gnomAD_pLI", "gnomAD_LOEUF"], ess),
        ("ΔD+Graph+Constraint", ["Delta_D", "Degree", "Betweenness", "Closeness", "Eigenvector", "gnomAD_pLI", "gnomAD_LOEUF"], ess),
    ]

    for model_name, feats, df0 in tasks:
        values = []
        for seed in seed_list:
            r = _oof_auc_for_seed(df0, feats, seed=seed)
            values.append({"seed": int(seed), **r})
        aucs = np.array([v["auc"] for v in values], dtype=float)
        aucs = aucs[np.isfinite(aucs)]
        auc_range = float(np.max(aucs) - np.min(aucs)) if aucs.size else float("nan")
        essentiality_seed_axes.append(
            {
                "model": model_name,
                "features": feats,
                "auc_range": auc_range,
                "pass": bool(np.isfinite(auc_range) and (auc_range <= tolerances["essentiality_auc_range_max"])),
                "by_seed": values,
            }
        )
        for v in values:
            grid_rows.append(
                {
                    "axis": "essentiality_cv_seed",
                    "model": model_name,
                    "seed": int(v["seed"]),
                    "n_rows": int(v["n_rows"]),
                    "n_networks": int(v["n_networks"]),
                    "auc": float(v["auc"]),
                    "ap": float(v["ap"]),
                    "brier": float(v["brier"]),
                }
            )

    grid = pd.DataFrame(grid_rows)
    grid_path = out_dir / "reproducibility_stress_grid.csv"
    grid.to_csv(grid_path, index=False)

    summary = {
        "protocol": {
            "networks_subset": chosen,
            "null_model": "degree_preserved",
            "baseline": {
                "seed_base": baseline_seed,
                "n_random": baseline_n_random,
                "n_swaps_mult": baseline_swaps_mult,
                "sort_by_degree": baseline_sort,
            },
            "ordering": {"n_permutations": 10, "n_permutations_control": 10},
            "essentiality": {"cv": "group_stratified_5fold_by_network", "seeds": [1, 2, 3, 4, 5]},
            "tolerances": tolerances,
        },
        "baseline_meta": baseline_meta,
        "axes": {
            "seed": seed_axes,
            "n_random": n_random_axes,
            "n_swaps": swap_axes,
            "ordering": ordering_summary,
            "essentiality_cv_seed": essentiality_seed_axes,
        },
        "pass": bool(
            all(a["pass"] for a in seed_axes)
            and all(a["pass"] for a in n_random_axes if a.get("required", True))
            and all(a["pass"] for a in swap_axes)
            and bool(ordering_summary["pass"])
            and all(a["pass"] for a in essentiality_seed_axes)
        ),
        "mitigation": {
            "if_null_seed_fails": "Increase n_random and/or enlarge network subset; investigate high tie rates in degree ordering.",
            "if_n_random_fails": "Increase null sample count (n_random) until mean_z and mean_fold stabilize under tolerances.",
            "if_swaps_fail": "Increase swap attempts or use higher n_swaps_mult; verify degree-preserving swap validity for small graphs.",
            "if_ordering_fails": "Use deterministic tie-breaker for degree ties (e.g., WL-style neighborhood hashing).",
            "if_essentiality_cv_seed_fails": "Increase sample size per model or tighten group stratification; consider regularization tuning under nested CV.",
        },
    }

    with open(out_dir / "reproducibility_stress_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    try:
        fig, axes = plt.subplots(2, 3, figsize=(13.8, 7.6))
        ax_seed = axes[0, 0]
        ax_nrand = axes[0, 1]
        ax_swaps = axes[0, 2]
        ax_order = axes[1, 0]
        ax_auc = axes[1, 1]
        axes[1, 2].axis("off")

        z_baseline = pd.DataFrame(baseline_rows)[["Network", "z_score"]].rename(columns={"z_score": "z_base"})
        alt_seed = next((a for a in seed_axes if a["seed_base"] != baseline_seed), None)
        if alt_seed is not None:
            seed_use = int(alt_seed["seed_base"])
            alt_rows = []
            for name in chosen:
                alt_rows.append(
                    _per_network_null(
                        seed_base=seed_use,
                        n_random=baseline_n_random,
                        n_swaps_mult=baseline_swaps_mult,
                        sort_by_degree=baseline_sort,
                        net_name=name,
                        net_data=networks[name],
                    )
                )
            z_alt = pd.DataFrame(alt_rows)[["Network", "z_score"]].rename(columns={"z_score": "z_alt"})
            zz = z_baseline.merge(z_alt, on="Network", how="inner")
            ax_seed.scatter(zz["z_base"], zz["z_alt"], s=18, alpha=0.8)
            if len(zz) >= 5:
                rho = float(stats.spearmanr(zz["z_base"], zz["z_alt"]).correlation)
            else:
                rho = float("nan")
            ax_seed.set_title(f"Seed robustness (z ranks)\nseed 42 vs {seed_use} (ρ={rho:.3f})")
            ax_seed.set_xlabel("z (seed 42)")
            ax_seed.set_ylabel(f"z (seed {seed_use})")

        xs = [a["n_random"] for a in n_random_axes]
        ys = [a["meta"]["mean_z"] for a in n_random_axes]
        ax_nrand.plot(xs, ys, marker="o", linewidth=1.5)
        ax_nrand.axhline(baseline_meta["mean_z"], linestyle="--", color="gray", linewidth=1.0)
        ax_nrand.set_title("Null ensemble size sensitivity")
        ax_nrand.set_xlabel("n_random")
        ax_nrand.set_ylabel("mean z (subset)")

        xs = [a["n_swaps_mult"] for a in swap_axes]
        ys = [a["meta"]["mean_z"] for a in swap_axes]
        ax_swaps.plot(xs, ys, marker="o", linewidth=1.5)
        ax_swaps.axhline(baseline_meta["mean_z"], linestyle="--", color="gray", linewidth=1.0)
        ax_swaps.set_title("Swap intensity sensitivity")
        ax_swaps.set_xlabel("n_swaps_mult")
        ax_swaps.set_ylabel("mean z (subset)")

        order = summary["axes"]["ordering"]
        idx_val = float(order["tie_breaker_index"]["mean_rel_sd_D"])
        wl_val = float(order["tie_breaker_wl"]["mean_rel_sd_D"])
        ctrl = float(order["control_sort_by_degree_false"]["mean_rel_range_D"])
        ax_order.bar(["tie=index", "tie=wl"], [idx_val, wl_val], color=["#4C72B0", "#55A868"])
        ax_order.axhline(tolerances["ordering_mean_rel_sd_max"], linestyle="--", color="black", linewidth=1.0)
        ax_order.set_title("Permutation stability of D\n(relative SD across permutations)")
        ax_order.set_ylabel("mean rel SD(D)")
        ax_order.set_ylim(bottom=0)
        ax_order.text(0.02, 0.98, f"control rel-range(no sort)≈{ctrl:.3f}", transform=ax_order.transAxes, va="top", ha="left", fontsize=9)

        target = next((m for m in essentiality_seed_axes if m["model"] == "ΔD+Graph+Constraint"), None)
        if target is not None:
            vals = target["by_seed"]
            xs = [v["seed"] for v in vals]
            ys = [v["auc"] for v in vals]
            ax_auc.plot(xs, ys, marker="o", linewidth=1.5)
            ax_auc.set_title(f"Essentiality CV seed sensitivity\nΔAUC range={target['auc_range']:.3f}")
            ax_auc.set_xlabel("CV seed")
            ax_auc.set_ylabel("OOF AUC")

        plt.tight_layout()
        fig.savefig(out_dir / "reproducibility_stress_axes.png", dpi=300, bbox_inches="tight")
        fig.savefig(out_dir / "reproducibility_stress_axes.pdf", bbox_inches="tight")
        plt.close(fig)
    except Exception:
        pass

    return summary


def run_bias_defense_suite(output_dir: Optional[str] = None) -> dict:
    out_dir = Path(output_dir) if output_dir is not None else _paper_figures_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    results_path = out_dir / "results_summary.csv"
    if not results_path.exists():
        run_full_analysis(output_dir=str(out_dir), skip_depmap=True, null_samples=50)

    df = pd.read_csv(results_path)
    df = df[df["null_model"] == "degree_preserved"].copy()
    df["name"] = df["name"].astype(str)

    networks = load_all_networks()
    meta = []
    for name, data in networks.items():
        meta.append(
            {
                "name": str(name),
                "Source": _infer_source(name, data),
                "Organism_Group": _infer_organism_group(name, data),
                "Size_Bin": _size_bin(float(len(data.get("nodes", []))) if isinstance(data.get("nodes"), list) else float("nan")),
            }
        )
    meta_df = pd.DataFrame(meta)
    df = df.merge(meta_df, on="name", how="left")
    df["Source"] = df["Source"].fillna("Unknown")
    df["Organism_Group"] = df["Organism_Group"].fillna("Unknown")
    df["Size_Bin"] = df["Size_Bin"].fillna("Unknown")

    df["fold_reduction"] = (df["D_random_mean"].astype(float) / df["D_bio"].astype(float)).replace([np.inf, -np.inf], np.nan)
    df["density"] = (df["n_edges"].astype(float) / (df["n_nodes"].astype(float) ** 2)).replace([np.inf, -np.inf], np.nan)

    def _metrics(sub: pd.DataFrame) -> dict:
        z = sub["z_score"].to_numpy(dtype=float)
        p = sub["p_value"].to_numpy(dtype=float)
        fold = sub["fold_reduction"].to_numpy(dtype=float)
        return {
            "n_networks": int(len(sub)),
            "mean_z": float(np.nanmean(z)) if len(sub) else float("nan"),
            "median_z": float(np.nanmedian(z)) if len(sub) else float("nan"),
            "fraction_z_gt_0": float(np.nanmean(z > 0)) if len(sub) else float("nan"),
            "fraction_p_le_0_05": float(np.nanmean(p <= 0.05)) if len(sub) else float("nan"),
            "mean_fold_reduction": float(np.nanmean(fold)) if len(sub) else float("nan"),
        }

    baseline = _metrics(df)
    tolerances = {
        "gate_a_mean_z_min": 0.50,
        "gate_a_frac_z_gt_0_min": 0.60,
        "gate_a_frac_p_le_0_05_min": 0.15,
    }

    def _passes_gate_a(m: dict) -> bool:
        return bool(
            (m["n_networks"] > 0)
            and np.isfinite(m["mean_z"])
            and np.isfinite(m["fraction_z_gt_0"])
            and np.isfinite(m["fraction_p_le_0_05"])
            and (m["mean_z"] >= tolerances["gate_a_mean_z_min"])
            and (m["fraction_z_gt_0"] >= tolerances["gate_a_frac_z_gt_0_min"])
            and (m["fraction_p_le_0_05"] >= tolerances["gate_a_frac_p_le_0_05_min"])
        )

    grid_rows: list[dict] = []
    axes: dict[str, list[dict]] = {"size_filter": [], "leave_one_source_out": [], "density_trim": []}

    size_grid = []
    for min_n in [5, 10, 15]:
        for max_n in [60, 80, 100]:
            if min_n > max_n:
                continue
            sub = df[(df["n_nodes"] >= min_n) & (df["n_nodes"] <= max_n)].copy()
            m = _metrics(sub)
            row = {
                "axis": "size_filter",
                "min_nodes": int(min_n),
                "max_nodes": int(max_n),
                **m,
                "passes_gate_a": _passes_gate_a(m),
                "delta_mean_z": float(m["mean_z"] - baseline["mean_z"]),
                "delta_fraction_z_gt_0": float(m["fraction_z_gt_0"] - baseline["fraction_z_gt_0"]),
                "delta_fraction_p_le_0_05": float(m["fraction_p_le_0_05"] - baseline["fraction_p_le_0_05"]),
            }
            grid_rows.append(row)
            size_grid.append(row)
    axes["size_filter"] = size_grid

    loo = []
    for src, sub_src in df.groupby("Source"):
        if len(sub_src) < 5:
            continue
        sub = df[df["Source"] != src].copy()
        m = _metrics(sub)
        row = {
            "axis": "leave_one_source_out",
            "excluded_source": str(src),
            **m,
            "passes_gate_a": _passes_gate_a(m),
            "delta_mean_z": float(m["mean_z"] - baseline["mean_z"]),
            "delta_fraction_z_gt_0": float(m["fraction_z_gt_0"] - baseline["fraction_z_gt_0"]),
            "delta_fraction_p_le_0_05": float(m["fraction_p_le_0_05"] - baseline["fraction_p_le_0_05"]),
        }
        grid_rows.append(row)
        loo.append(row)
    axes["leave_one_source_out"] = loo

    dens = df["density"].to_numpy(dtype=float)
    qlo = float(np.nanquantile(dens, 0.05)) if np.isfinite(dens).any() else float("nan")
    qhi = float(np.nanquantile(dens, 0.95)) if np.isfinite(dens).any() else float("nan")
    trims = []
    for lo, hi, label in [
        (0.00, 1.00, "none"),
        (0.05, 0.95, "5-95%"),
        (0.10, 0.90, "10-90%"),
    ]:
        loq = float(np.nanquantile(dens, lo)) if np.isfinite(dens).any() else float("nan")
        hiq = float(np.nanquantile(dens, hi)) if np.isfinite(dens).any() else float("nan")
        sub = df[(df["density"] >= loq) & (df["density"] <= hiq)].copy()
        m = _metrics(sub)
        row = {
            "axis": "density_trim",
            "trim": str(label),
            "density_lo": float(loq),
            "density_hi": float(hiq),
            "density_lo_5pct": qlo,
            "density_hi_95pct": qhi,
            **m,
            "passes_gate_a": _passes_gate_a(m),
            "delta_mean_z": float(m["mean_z"] - baseline["mean_z"]),
            "delta_fraction_z_gt_0": float(m["fraction_z_gt_0"] - baseline["fraction_z_gt_0"]),
            "delta_fraction_p_le_0_05": float(m["fraction_p_le_0_05"] - baseline["fraction_p_le_0_05"]),
        }
        grid_rows.append(row)
        trims.append(row)
    axes["density_trim"] = trims

    strat_rows = []
    for strat_name in ["Source", "Organism_Group", "Size_Bin"]:
        for level, sub in df.groupby(strat_name):
            if len(sub) < 5:
                continue
            m = _metrics(sub)
            z = sub["z_score"].to_numpy(dtype=float)
            mu, lo, hi = _bootstrap_mean_ci(z, n_boot=5000, seed=42)
            strat_rows.append(
                {
                    "Stratum": str(strat_name),
                    "Level": str(level),
                    "n_networks": int(m["n_networks"]),
                    "mean_z": float(m["mean_z"]),
                    "mean_z_ci95_lo": float(lo),
                    "mean_z_ci95_hi": float(hi),
                    "median_z": float(m["median_z"]),
                    "fraction_z_gt_0": float(m["fraction_z_gt_0"]),
                    "fraction_p_le_0_05": float(m["fraction_p_le_0_05"]),
                    "mean_fold_reduction": float(m["mean_fold_reduction"]),
                }
            )
    if strat_rows:
        pd.DataFrame(strat_rows).sort_values(["Stratum", "Level"]).to_csv(out_dir / "bias_defense_stratified.csv", index=False)

    grid = pd.DataFrame(grid_rows)
    grid.to_csv(out_dir / "bias_defense_grid.csv", index=False)

    summary = {
        "protocol": {
            "input": str(results_path),
            "null_model": "degree_preserved",
            "axes": ["size_filter", "leave_one_source_out", "density_trim"],
            "tolerances": tolerances,
        },
        "baseline": baseline,
        "axes": axes,
        "pass": bool(
            all(r["passes_gate_a"] for r in axes["size_filter"])
            and all(r["passes_gate_a"] for r in axes["leave_one_source_out"])
            and all(r["passes_gate_a"] for r in axes["density_trim"])
        ),
    }
    with open(out_dir / "bias_defense_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    try:
        strat = pd.DataFrame(strat_rows)
        if len(strat):
            fig, ax = plt.subplots(1, 1, figsize=(8.6, 4.2))
            sub = strat[strat["Stratum"] == "Source"].copy()
            if len(sub):
                sub = sub.sort_values("n_networks", ascending=False)
                ax.errorbar(
                    sub["mean_z"].to_numpy(dtype=float),
                    np.arange(len(sub)),
                    xerr=[
                        sub["mean_z"].to_numpy(dtype=float) - sub["mean_z_ci95_lo"].to_numpy(dtype=float),
                        sub["mean_z_ci95_hi"].to_numpy(dtype=float) - sub["mean_z"].to_numpy(dtype=float),
                    ],
                    fmt="o",
                    color="#4C72B0",
                    ecolor="gray",
                    elinewidth=1.2,
                    capsize=3,
                )
                ax.set_yticks(np.arange(len(sub)))
                ax.set_yticklabels([f"{lvl} (n={int(n)})" for lvl, n in zip(sub["Level"], sub["n_networks"])])
                ax.axvline(tolerances["gate_a_mean_z_min"], linestyle="--", color="black", linewidth=1.0)
                ax.set_xlabel("mean z (95% bootstrap CI)")
                ax.set_title("Gate A signal by source (degree-preserved null)")
                plt.tight_layout()
                fig.savefig(out_dir / "figure_bias_defense_by_source.png", dpi=300, bbox_inches="tight")
                fig.savefig(out_dir / "figure_bias_defense_by_source.pdf", bbox_inches="tight")
                plt.close(fig)

        fig, axes2 = plt.subplots(1, 2, figsize=(12.4, 4.3))
        ax_hm, ax_loo = axes2
        sg = pd.DataFrame(size_grid)
        if len(sg):
            pivot = sg.pivot(index="min_nodes", columns="max_nodes", values="mean_z")
            sns.heatmap(pivot, annot=True, fmt=".3f", cmap="viridis", ax=ax_hm, cbar_kws={"label": "mean z"})
            ax_hm.set_title("Mean z under size filters")
            ax_hm.set_xlabel("max_nodes")
            ax_hm.set_ylabel("min_nodes")

        lo = pd.DataFrame(loo)
        if len(lo):
            lo = lo.sort_values("excluded_source")
            ax_loo.barh(lo["excluded_source"], lo["mean_z"] - baseline["mean_z"], color="#55A868")
            ax_loo.axvline(0.0, linestyle="--", color="gray", linewidth=1.0)
            ax_loo.set_title("Leave-one-source-out Δ mean z")
            ax_loo.set_xlabel("Δ mean z (vs baseline)")
        plt.tight_layout()
        fig.savefig(out_dir / "figure_bias_defense_sensitivity.png", dpi=300, bbox_inches="tight")
        fig.savefig(out_dir / "figure_bias_defense_sensitivity.pdf", bbox_inches="tight")
        plt.close(fig)
    except Exception:
        pass

    return summary



def generate_figure3_depmap(output_dir: Path) -> bool:
    repo_root = _repo_root()
    script = repo_root / "src" / "analysis" / "DepMap_Validation.py"
    if not script.exists():
        return False

    out_prefix = output_dir / "figure3_depmap_validation"
    env = os.environ.copy()
    env["DEPMAP_OUT_PREFIX"] = str(out_prefix)
    depmap_release_dir = repo_root / "data" / "DepMap"
    if depmap_release_dir.exists():
        env.setdefault("DEPMAP_RELEASE_DIR", str(depmap_release_dir))
        env.setdefault("DEPMAP_AUDIT_DIR", str(depmap_release_dir))

    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.returncode != 0:
        if proc.stderr:
            print(proc.stderr.rstrip())
        raise RuntimeError(f"DepMap Figure 3 generation failed (exit={proc.returncode}).")

    expected = out_prefix.with_name(out_prefix.name + "_stats.json")
    if not expected.exists():
        raise FileNotFoundError(f"DepMap Figure 3 stats not produced: {expected}")

    print(f"Saved Figure 3 stats to {expected}")
    return True


# ============================================================================
# SECTION 5: MAIN ANALYSIS
# ============================================================================

def run_full_analysis(output_dir: Optional[str] = None, skip_depmap: bool = False, null_samples: int = 50):
    """Run complete analysis pipeline."""
    print("=" * 60)
    print("PAPER 1: Algorithmic Efficiency of Biological Networks")
    print("=" * 60)

    # Create output directory
    output_dir = Path(output_dir) if output_dir is not None else (Path(__file__).resolve().parent.parent / "figures")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    steps = 6 if not skip_depmap else 5
    print(f"\n[1/{steps}] Loading networks...")
    networks = load_all_networks()
    ess_df = load_essentiality_data()

    # Compute D_bio vs D_null for all networks and null families
    print(f"\n[2/{steps}] Computing algorithmic complexity...")
    results_long = []
    for i, (name, data) in enumerate(networks.items()):
        if i % 50 == 0:
            print(f"  Processing network {i+1}/{len(networks)}...")

        cm = get_adjacency_matrix(data)
        if cm.shape[0] < 5 or cm.shape[0] > 100:
            continue  # Skip very small or very large

        base = {
            "name": name,
            "n_nodes": int(cm.shape[0]),
            "n_edges": int(cm.sum()),
        }

        for null_model in ("er", "degree_preserved"):
            result = compute_D_bio_vs_random(cm, n_random=null_samples, null_model=null_model)
            result.update(base)
            results_long.append(result)

        gate_features = extract_gate_features(data)
        if gate_features is not None:
            result = compute_D_bio_vs_random(
                cm,
                n_random=null_samples,
                null_model="gate_permuted",
                node_features=gate_features,
            )
            result.update(base)
            results_long.append(result)

    results_long_df = pd.DataFrame(results_long)
    results_df = results_long_df[results_long_df["null_model"] == "degree_preserved"].copy()

    # Summary statistics
    print(f"\n[3/{steps}] Computing summary statistics...")
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
    print(f"\n[4/{steps}] Generating figures...")
    generate_figure1(results_long_df, str(output_dir))

    # Essentiality analysis (locked predictors + grouped uncertainty)
    print(f"\n[5/{steps}] Essentiality analysis...")
    generate_figure2(ess_df, networks, str(output_dir))
    generate_figure2_baseline_benchmarks(ess_df, networks, str(output_dir))

    if not skip_depmap:
        print(f"\n[6/{steps}] DepMap analysis...")
        generate_figure3_depmap(output_dir)

    # Save results
    results_df.to_csv(output_dir / "results_summary.csv", index=False)
    results_long_df.to_csv(output_dir / "null_results_long.csv", index=False)

    summary = {}
    for null_model, sub in results_long_df.groupby("null_model"):
        folds = (sub["D_random_mean"].to_numpy(dtype=float) / sub["D_bio"].to_numpy(dtype=float))
        diffs = (sub["D_random_mean"].to_numpy(dtype=float) - sub["D_bio"].to_numpy(dtype=float))
        diffs = diffs[np.isfinite(diffs)]
        mean_fold, fold_lo, fold_hi = _bootstrap_mean_ci(folds, n_boot=10000, seed=42)
        sd = float(np.std(diffs, ddof=1)) if diffs.size > 1 else float("nan")
        cohens_d = float(np.mean(diffs) / sd) if sd and np.isfinite(sd) and sd > 0 else float("nan")
        ttest = stats.ttest_rel(sub["D_bio"], sub["D_random_mean"])

        summary[null_model] = {
            "n_networks": int(len(sub)),
            "mean_fold_reduction": mean_fold,
            "fold_reduction_ci95": [fold_lo, fold_hi],
            "mean_z": float(np.mean(sub["z_score"])),
            "fraction_p_lt_0_05": float(np.mean(sub["p_value"] < 0.05)),
            "paired_t_pvalue": float(ttest.pvalue),
            "paired_t_stat": float(ttest.statistic),
            "cohens_d_paired": cohens_d,
        }

    with open(output_dir / "null_meta_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nResults saved to {output_dir}/")

    return results_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluate-gates", action="store_true")
    parser.add_argument("--stress-tests", action="store_true")
    parser.add_argument("--bias-tests", action="store_true")
    parser.add_argument("--figures-dir", type=str, default=None)
    parser.add_argument("--bootstrap", type=int, default=10000)
    parser.add_argument("--repro-nets", type=int, default=30)
    parser.add_argument("--skip-depmap", action="store_true")
    parser.add_argument("--null-samples", type=int, default=50)
    args = parser.parse_args()

    np.random.seed(42)
    if args.evaluate_gates:
        evaluate_gate_thresholds(
            figures_dir=args.figures_dir,
            n_boot=args.bootstrap,
            reproducibility_networks=args.repro_nets,
        )
    elif args.stress_tests:
        run_reproducibility_stress_tests(output_dir=args.figures_dir, n_networks=args.repro_nets)
    elif args.bias_tests:
        run_bias_defense_suite(output_dir=args.figures_dir)
    else:
        run_full_analysis(output_dir=args.figures_dir, skip_depmap=args.skip_depmap, null_samples=args.null_samples)
