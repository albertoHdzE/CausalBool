import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc
import os

def analyze_results():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    results_path = os.path.join(base_dir, 'results/level7/fidelity_validation_results_full.csv')
    output_dir = os.path.join(base_dir, 'results/level7/analysis')
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(results_path):
        print(f"Results file not found: {results_path}")
        return
        
    df = pd.read_csv(results_path)
    print(f"Loaded {len(df)} gene records from {df['Network'].nunique()} networks.")
    
    # Filter Valid Data
    valid_df = df[df['Source'].isin(['Manual', 'DepMap'])]
    print(f"Valid Data (Manual/DepMap): {len(valid_df)} records from {valid_df['Network'].nunique()} networks.")
    
    if valid_df.empty:
        print("No valid data for analysis.")
        return

    # 1. Global ROC Curve
    fpr, tpr, _ = roc_curve(valid_df['Is_Essential'], valid_df['Loss_Fidelity'])
    roc_auc = auc(fpr, tpr)
    
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'Global ROC (AUC = {roc_auc:.3f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Semantic Basin Fidelity: Global Performance (N=231 Cohort)')
    plt.legend(loc="lower right")
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(output_dir, 'global_roc_curve.png'))
    plt.close()
    
    # 2. Distribution Plot
    plt.figure(figsize=(10, 6))
    ess = valid_df[valid_df['Is_Essential'] == 1]['Loss_Fidelity']
    non_ess = valid_df[valid_df['Is_Essential'] == 0]['Loss_Fidelity']
    
    plt.hist(non_ess, bins=30, alpha=0.5, label=f'Non-Essential (N={len(non_ess)})', density=True, color='blue')
    plt.hist(ess, bins=30, alpha=0.5, label=f'Essential (N={len(ess)})', density=True, color='red')
    
    plt.xlabel('Fidelity Loss (1 - Fidelity)')
    plt.ylabel('Density')
    plt.title('Distribution of Fidelity Loss')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(output_dir, 'fidelity_distribution.png'))
    plt.close()
    
    # 3. Source Comparison (Manual vs DepMap)
    manual_df = valid_df[valid_df['Source'] == 'Manual']
    depmap_df = valid_df[valid_df['Source'] == 'DepMap']
    
    plt.figure(figsize=(8, 6))
    if not manual_df.empty:
        fpr_m, tpr_m, _ = roc_curve(manual_df['Is_Essential'], manual_df['Loss_Fidelity'])
        auc_m = auc(fpr_m, tpr_m)
        plt.plot(fpr_m, tpr_m, label=f'Manual Curated (N={manual_df["Network"].nunique()}, AUC={auc_m:.3f})')
        
    if not depmap_df.empty:
        fpr_d, tpr_d, _ = roc_curve(depmap_df['Is_Essential'], depmap_df['Loss_Fidelity'])
        auc_d = auc(fpr_d, tpr_d)
        plt.plot(fpr_d, tpr_d, label=f'DepMap Inferred (N={depmap_df["Network"].nunique()}, AUC={auc_d:.3f})')
        
    plt.plot([0, 1], [0, 1], 'k--')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Performance by Ground Truth Source')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(output_dir, 'source_comparison_roc.png'))
    plt.close()
    
    # 4. Summary Table
    summary = {
        'Metric': ['Total Networks', 'Analyzed Genes', 'Essential Genes', 'Global AUC'],
        'Value': [
            valid_df['Network'].nunique(),
            len(valid_df),
            valid_df['Is_Essential'].sum(),
            f"{roc_auc:.4f}"
        ]
    }
    pd.DataFrame(summary).to_csv(os.path.join(output_dir, 'summary_stats.csv'), index=False)
    
    print("Analysis Complete.")

if __name__ == "__main__":
    analyze_results()
