#!/usr/bin/env python3
"""
Essentiality Prediction Analysis - Extended Version
====================================================

Analyzes ΔD as a predictor of gene essentiality across multiple networks.
Includes cross-validation, bootstrapped confidence intervals, and
statistical comparisons with graph metrics.

Author: [Authors]
Date: March 2026
"""

import numpy as np
import pandas as pd
from scipy import stats
from pathlib import Path
from sklearn.metrics import roc_auc_score, roc_curve, auc
from sklearn.model_selection import StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# Set style
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


def _default_figures_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "figures"


def load_essentiality_data(filepath: str | None = None) -> pd.DataFrame:
    """Load the essentiality prediction dataset."""
    if filepath is None:
        candidates = [
            _default_figures_dir() / "essentiality_prediction_dataset.csv",
            Path(__file__).resolve().parents[4] / "results" / "bio" / "essentiality_prediction_dataset.csv",
        ]
        existing = next((p for p in candidates if p.exists()), None)
        if existing is None:
            raise FileNotFoundError(
                "Essentiality dataset not found. Looked for: "
                + ", ".join(str(p) for p in candidates)
            )
        filepath = str(existing)
    df = pd.read_csv(filepath)
    print(f"Loaded {len(df)} genes from {df['Network'].nunique()} networks")
    print(f"  Essential: {(df['Is_Essential'] == 1).sum()}")
    print(f"  Non-essential: {(df['Is_Essential'] == 0).sum()}")
    return df


def bootstrap_auc(y_true, y_score, n_boot=1000, seed=42):
    """
    Compute AUC with 95% confidence interval via bootstrapping.
    """
    np.random.seed(seed)
    aucs = []

    n = len(y_true)
    for _ in range(n_boot):
        idx = np.random.choice(n, n, replace=True)
        if len(np.unique(np.array(y_true)[idx])) < 2:
            continue
        try:
            auc_val = roc_auc_score(np.array(y_true)[idx], np.array(y_score)[idx])
            aucs.append(auc_val)
        except:
            continue

    return np.mean(aucs), np.percentile(aucs, [2.5, 97.5])


def cross_validated_auc(X, y, n_splits=5, seed=42):
    """
    Compute cross-validated AUC using logistic regression.
    """
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    aucs = []

    for train_idx, test_idx in skf.split(X, y):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        # Standardize
        mean = X_train.mean(axis=0, keepdims=True)
        std = X_train.std(axis=0, keepdims=True) + 1e-8
        X_train_scaled = (X_train - mean) / std
        X_test_scaled = (X_test - mean) / std

        # Train logistic regression
        clf = LogisticRegression(random_state=seed, max_iter=1000, class_weight="balanced")
        clf.fit(X_train_scaled, y_train)

        # Predict probabilities
        y_prob = clf.predict_proba(X_test_scaled)[:, 1]
        auc_val = roc_auc_score(y_test, y_prob)
        aucs.append(auc_val)

    return np.mean(aucs), np.std(aucs)


def stratified_group_kfold_splits(groups, y, n_splits=5, seed=42):
    groups = np.asarray(groups)
    y = np.asarray(y).astype(int)
    uniq = np.unique(groups)

    rng = np.random.RandomState(seed)
    rng.shuffle(uniq)

    pos_per_group = {g: int(y[groups == g].sum()) for g in uniq}
    size_per_group = {g: int((groups == g).sum()) for g in uniq}

    order = sorted(uniq, key=lambda g: (pos_per_group[g], size_per_group[g]), reverse=True)

    fold_groups = [[] for _ in range(n_splits)]
    fold_pos = [0 for _ in range(n_splits)]
    fold_size = [0 for _ in range(n_splits)]

    for g in order:
        k = min(range(n_splits), key=lambda i: (fold_pos[i], fold_size[i]))
        fold_groups[k].append(g)
        fold_pos[k] += pos_per_group[g]
        fold_size[k] += size_per_group[g]

    splits = []
    for k in range(n_splits):
        test_groups = set(fold_groups[k])
        test_mask = np.isin(groups, list(test_groups))
        train_idx = np.where(~test_mask)[0]
        test_idx = np.where(test_mask)[0]
        splits.append((train_idx, test_idx))
    return splits


def cross_validated_auc_grouped(X, y, groups, n_splits=5, seed=42):
    splits = stratified_group_kfold_splits(groups, y, n_splits=n_splits, seed=seed)
    aucs = []
    used_folds = 0
    skipped_folds = 0

    for train_idx, test_idx in splits:
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        if len(np.unique(y_test)) < 2 or len(np.unique(y_train)) < 2:
            skipped_folds += 1
            continue

        mean = X_train.mean(axis=0, keepdims=True)
        std = X_train.std(axis=0, keepdims=True) + 1e-8
        X_train_scaled = (X_train - mean) / std
        X_test_scaled = (X_test - mean) / std

        clf = LogisticRegression(random_state=seed, max_iter=1000, class_weight="balanced")
        clf.fit(X_train_scaled, y_train)
        y_prob = clf.predict_proba(X_test_scaled)[:, 1]
        aucs.append(roc_auc_score(y_test, y_prob))
        used_folds += 1

    if len(aucs) == 0:
        return float("nan"), float("nan"), used_folds, skipped_folds
    return float(np.mean(aucs)), float(np.std(aucs)), used_folds, skipped_folds


def delong_test(y_true, y_pred1, y_pred2):
    """
    Approximate DeLong test for comparing two AUCs.
    Uses bootstrap-based comparison as approximation.
    """
    np.random.seed(42)
    n_boot = 1000
    diff_aucs = []

    n = len(y_true)
    for _ in range(n_boot):
        idx = np.random.choice(n, n, replace=True)
        if len(np.unique(y_true[idx])) < 2:
            continue
        try:
            auc1 = roc_auc_score(y_true[idx], y_pred1[idx])
            auc2 = roc_auc_score(y_true[idx], y_pred2[idx])
            diff_aucs.append(auc1 - auc2)
        except:
            continue

    diff_aucs = np.array(diff_aucs)
    p_value = 2 * min(np.mean(diff_aucs > 0), np.mean(diff_aucs < 0))
    return p_value


def generate_figure2_extended(df: pd.DataFrame, output_dir: str | None = None):
    """
    Generate publication-quality Figure 2 with extended analysis.

    Panel A: ΔD distribution by essentiality
    Panel B: ROC curves with confidence intervals
    Panel C: Cross-validated AUC comparison
    Panel D: Feature importance analysis
    """
    if output_dir is None:
        output_dir = str(_default_figures_dir())
    # Prepare data
    df = df.copy()
    df['Is_Essential'] = df['Is_Essential'].astype(int)

    # Remove rows with missing values
    df = df.dropna(subset=['Delta_D', 'Degree', 'Betweenness', 'Is_Essential'])

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # ===== Panel A: Distribution =====
    ax = axes[0, 0]
    ess = df[df['Is_Essential'] == 1]['Delta_D']
    non_ess = df[df['Is_Essential'] == 0]['Delta_D']

    # Violin plot
    positions = [0, 1]
    parts = ax.violinplot([non_ess, ess], positions=positions,
                          showmeans=True, showmedians=False, widths=0.7)

    colors = ['#e74c3c', '#2ecc71']
    for i, pc in enumerate(parts['bodies']):
        pc.set_facecolor(colors[i])
        pc.set_alpha(0.6)

    ax.set_xticks([0, 1])
    ax.set_xticklabels([f'Non-essential\n(n={len(non_ess)})',
                        f'Essential\n(n={len(ess)})'])
    ax.set_ylabel('ΔD (bytes)')
    ax.set_title('Essential Genes Tend to Have Higher ΔD')

    # Statistical test
    stat, p_val = stats.mannwhitneyu(ess, non_ess, alternative='greater')
    ax.text(0.5, 0.95, f'Mann-Whitney U: p = {p_val:.2e}',
            transform=ax.transAxes, va='top', ha='center',
            fontsize=10, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    # ===== Panel B: ROC Curves =====
    ax = axes[0, 1]

    y_true = df['Is_Essential'].values
    metrics = {
        'ΔD': df['Delta_D'].values,
        'Degree': df['Degree'].values,
        'Betweenness': df['Betweenness'].values,
    }

    colors = {'ΔD': '#2ecc71', 'Degree': '#3498db', 'Betweenness': '#e74c3c'}

    results_table = []
    for name, scores in metrics.items():
        # Compute AUC with CI
        mean_auc, ci = bootstrap_auc(y_true, scores)
        fpr, tpr, _ = roc_curve(y_true, scores)

        ax.plot(fpr, tpr, label=f'{name}: AUC={mean_auc:.2f} [{ci[0]:.2f}-{ci[1]:.2f}]',
                color=colors[name], lw=2)

        results_table.append({
            'Metric': name,
            'AUC': mean_auc,
            'CI_lower': ci[0],
            'CI_upper': ci[1]
        })

    ax.plot([0, 1], [0, 1], 'k--', label='Random (AUC=0.50)', alpha=0.5)
    ax.set_xlabel('False Positive Rate')
    ax.set_ylabel('True Positive Rate')
    ax.set_title('ROC Curves with 95% CI')
    ax.legend(loc='lower right', fontsize=8)

    # ===== Panel C: Cross-validated AUC =====
    ax = axes[1, 0]

    # Prepare features
    X_delta_d = df[['Delta_D']].values
    X_degree = df[['Degree']].values
    X_betweenness = df[['Betweenness']].values
    X_combined = df[['Delta_D', 'Degree', 'Betweenness']].values
    y = df['Is_Essential'].values

    # Cross-validated AUCs
    cv_results = {}
    cv_results['ΔD'], cv_results['ΔD_std'] = cross_validated_auc(X_delta_d, y)
    cv_results['Degree'], cv_results['Degree_std'] = cross_validated_auc(X_degree, y)
    cv_results['Betweenness'], cv_results['Betweenness_std'] = cross_validated_auc(X_betweenness, y)
    cv_results['Combined'], cv_results['Combined_std'] = cross_validated_auc(X_combined, y)

    groups = df["Network"].astype(str).values
    grouped = {}
    grouped["ΔD"], grouped["ΔD_std"], grouped["ΔD_used"], grouped["ΔD_skipped"] = cross_validated_auc_grouped(
        X_delta_d, y, groups, n_splits=5, seed=42
    )
    grouped["Degree"], grouped["Degree_std"], grouped["Degree_used"], grouped["Degree_skipped"] = cross_validated_auc_grouped(
        X_degree, y, groups, n_splits=5, seed=42
    )
    grouped["Betweenness"], grouped["Betweenness_std"], grouped["Betweenness_used"], grouped["Betweenness_skipped"] = cross_validated_auc_grouped(
        X_betweenness, y, groups, n_splits=5, seed=42
    )
    grouped["Combined"], grouped["Combined_std"], grouped["Combined_used"], grouped["Combined_skipped"] = cross_validated_auc_grouped(
        X_combined, y, groups, n_splits=5, seed=42
    )

    # Bar plot
    metrics_names = list(cv_results.keys())[::2]  # Get main metric names
    means = [cv_results[m] for m in metrics_names]
    stds = [cv_results[m + '_std'] for m in metrics_names]

    colors = ['#2ecc71', '#3498db', '#e74c3c', '#9b59b6']
    bars = ax.bar(metrics_names, means, yerr=stds, color=colors,
                  capsize=5, edgecolor='black', linewidth=1)

    ax.set_ylim(0, 1)
    ax.axhline(y=0.5, color='gray', linestyle='--', label='Random')
    ax.set_ylabel('Cross-Validated AUC')
    ax.set_title('5-Fold Cross-Validation Results')
    ax.legend()

    # Add value labels
    for bar, mean, std in zip(bars, means, stds):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + std + 0.02,
                f'{mean:.2f}±{std:.2f}', ha='center', va='bottom', fontsize=9)

    # ===== Panel D: Statistical Summary =====
    ax = axes[1, 1]
    ax.axis('off')

    # Create summary table
    summary_text = "STATISTICAL SUMMARY\n" + "="*40 + "\n\n"

    # Dataset info
    summary_text += f"Dataset:\n"
    summary_text += f"  Total genes: {len(df)}\n"
    summary_text += f"  Essential: {y.sum()} ({100*y.mean():.1f}%)\n"
    summary_text += f"  Networks: {df['Network'].nunique()}\n\n"

    # AUC comparison
    summary_text += "AUC Comparison (95% CI):\n"
    for r in results_table:
        summary_text += f"  {r['Metric']}: {r['AUC']:.3f} [{r['CI_lower']:.3f}-{r['CI_upper']:.3f}]\n"

    summary_text += "\nCross-Validation (5-fold):\n"
    for m in metrics_names:
        summary_text += f"  {m}: {cv_results[m]:.3f} ± {cv_results[m+'_std']:.3f}\n"

    summary_text += "\nNetwork-held-out CV (5 folds):\n"
    for m in ["ΔD", "Degree", "Betweenness", "Combined"]:
        summary_text += (
            f"  {m}: {grouped[m]:.3f} ± {grouped[m+'_std']:.3f} "
            f"(used {int(grouped[m+'_used'])}, skipped {int(grouped[m+'_skipped'])})\n"
        )

    # Statistical tests
    summary_text += "\nMann-Whitney U Test:\n"
    summary_text += f"  Essential vs Non-essential ΔD\n"
    summary_text += f"  p-value: {p_val:.2e}\n"

    ax.text(0.1, 0.95, summary_text, transform=ax.transAxes,
            fontfamily='monospace', fontsize=10, va='top',
            bbox=dict(boxstyle='round', facecolor='#f8f9fa', alpha=0.8))

    plt.tight_layout()
    plt.savefig(f"{output_dir}/figure2_essentiality_extended.pdf")
    plt.savefig(f"{output_dir}/figure2_essentiality_extended.png")
    print(f"Saved extended Figure 2 to {output_dir}/")
    plt.close()

    return results_table, cv_results


def generate_supplementary_table(df: pd.DataFrame, output_dir: str | None = None):
    """Generate supplementary table with per-network results."""
    if output_dir is None:
        output_dir = str(_default_figures_dir())

    results = []
    for network in df['Network'].unique():
        net_df = df[df['Network'] == network]
        n_genes = len(net_df)
        n_essential = net_df['Is_Essential'].sum()

        if n_essential > 0 and n_genes - n_essential > 0:
            try:
                auc_delta = roc_auc_score(net_df['Is_Essential'], net_df['Delta_D'])
                auc_degree = roc_auc_score(net_df['Is_Essential'], net_df['Degree'])
            except:
                continue

            results.append({
                'Network': network.replace('.json', ''),
                'N_genes': n_genes,
                'N_essential': n_essential,
                'AUC_DeltaD': auc_delta,
                'AUC_Degree': auc_degree
            })

    results_df = pd.DataFrame(results)
    results_df.to_csv(f"{output_dir}/supplementary_table_per_network.csv", index=False)
    print(f"Saved supplementary table to {output_dir}/")

    return results_df


if __name__ == "__main__":
    np.random.seed(42)

    print("="*60)
    print("ESSENTIALITY PREDICTION - EXTENDED ANALYSIS")
    print("="*60)

    # Load data
    df = load_essentiality_data()

    # Generate figures
    print("\nGenerating extended analysis figures...")
    results_table, cv_results = generate_figure2_extended(df)

    # Generate supplementary table
    supp_table = generate_supplementary_table(df)

    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    print("\nBootstrap AUC (95% CI):")
    for r in results_table:
        print(f"  {r['Metric']}: {r['AUC']:.3f} [{r['CI_lower']:.3f}-{r['CI_upper']:.3f}]")

    print("\nCross-validated AUC (5-fold):")
    for m in ['ΔD', 'Degree', 'Betweenness', 'Combined']:
        print(f"  {m}: {cv_results[m]:.3f} ± {cv_results[m+'_std']:.3f}")
