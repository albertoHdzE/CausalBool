import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc
from datetime import datetime

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from analysis.Hybrid_Essentiality_Validator import HybridEssentialityValidator

def run_experiment():
    # Setup paths
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_dir = os.path.join(base_dir, 'data/bio/processed')
    metadata_path = os.path.join(base_dir, 'data/bio/curated/metadata.csv')
    output_dir = os.path.join(base_dir, 'results/level5')
    os.makedirs(output_dir, exist_ok=True)
    
    validator = HybridEssentialityValidator(data_dir, metadata_path)
    metadata = validator.load_metadata()
    
    all_results = []
    
    print(f"[{datetime.now()}] Starting Level 5 Hybrid Validation on {len(metadata)} networks...")
    
    for idx, row in metadata.iterrows():
        filename = row['Filename']
        ess_genes = row['Essential Genes (comma separated)']
        print(f"Processing {filename}...")
        
        # Skip if file missing
        if not os.path.exists(os.path.join(data_dir, filename)):
            print(f"  Skipping (not found)")
            continue
            
        try:
            res = validator.validate_network(filename, ess_genes, alpha=0.5, beta=0.5, steps=200)
            all_results.extend(res)
        except Exception as e:
            print(f"  Error: {e}")
            
    # Save results
    df = pd.DataFrame(all_results)
    csv_path = os.path.join(output_dir, 'hybrid_validation_results.csv')
    df.to_csv(csv_path, index=False)
    print(f"Results saved to {csv_path}")
    
    # Analysis
    if len(df) == 0:
        print("No results generated.")
        return
        
    # Filter for valid comparisons (where we have essential genes)
    # We only care about networks that have at least one essential gene identified
    # But wait, if Is_Essential is 0 for all genes in a network, we can't compute ROC per network.
    # But global ROC is possible.
    
    # Global ROC
    y_true = df['Is_Essential']
    y_scores = df['Delta_H']
    
    if y_true.sum() == 0:
        print("No essential genes found in the processed networks (naming mismatch?).")
        return
        
    fpr, tpr, _ = roc_curve(y_true, y_scores)
    roc_auc = auc(fpr, tpr)
    print(f"Global AUC: {roc_auc:.4f}")
    
    # Plot ROC
    plt.figure()
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {roc_auc:.2f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver Operating Characteristic - Hybrid Complexity')
    plt.legend(loc="lower right")
    plt.savefig(os.path.join(output_dir, 'roc_curve_hybrid.png'))
    plt.close()
    
    # Boxplot
    ess_delta = df[df['Is_Essential'] == 1]['Delta_H']
    non_ess_delta = df[df['Is_Essential'] == 0]['Delta_H']
    
    plt.figure()
    plt.boxplot([ess_delta, non_ess_delta], labels=['Essential', 'Non-Essential'])
    plt.ylabel('Delta Hybrid Complexity')
    plt.title(f'Impact of Gene Knockout (AUC={roc_auc:.2f})')
    plt.savefig(os.path.join(output_dir, 'boxplot_hybrid.png'))
    plt.close()
    
    # Statistics
    print(f"Essential Mean Delta_H: {ess_delta.mean():.4f}")
    print(f"Non-Essential Mean Delta_H: {non_ess_delta.mean():.4f}")
    
    # T-test
    from scipy.stats import ttest_ind
    t_stat, p_val = ttest_ind(ess_delta, non_ess_delta)
    print(f"T-test: t={t_stat:.4f}, p={p_val:.4e}")

if __name__ == '__main__':
    run_experiment()
