import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, roc_curve, auc
import os

def optimize_alpha(csv_path, output_dir):
    df = pd.read_csv(csv_path)
    
    if 'Is_Essential' not in df.columns or 'Delta_Struct' not in df.columns or 'Delta_Dyn' not in df.columns:
        print("Error: Missing required columns (Is_Essential, Delta_Struct, Delta_Dyn)")
        return
        
    y_true = df['Is_Essential']
    
    # We want to maximize AUC.
    # Metric: Delta_Hybrid = alpha * Delta_Struct + (1-alpha) * Delta_Dyn
    # Wait, raw values are very different scales.
    # Mean Delta_Struct ~ 2-5? Mean Delta_Dyn ~ 0.001?
    # Let's check ranges.
    
    mean_struct = df['Delta_Struct'].abs().mean()
    mean_dyn = df['Delta_Dyn'].abs().mean()
    
    print(f"Mean |Delta_Struct|: {mean_struct:.4f}")
    print(f"Mean |Delta_Dyn|: {mean_dyn:.4f}")
    
    # If dyn is very small, we need to scale it UP to be comparable.
    # Or normalize both to Z-scores.
    
    # Z-score normalization
    if df['Delta_Struct'].std() > 0:
        z_struct = (df['Delta_Struct'] - df['Delta_Struct'].mean()) / df['Delta_Struct'].std()
    else:
        z_struct = np.zeros(len(df))
        
    if df['Delta_Dyn'].std() > 0:
        z_dyn = (df['Delta_Dyn'] - df['Delta_Dyn'].mean()) / df['Delta_Dyn'].std()
    else:
        z_dyn = np.zeros(len(df))
        
    alphas = np.linspace(0, 1, 101)
    aucs = []
    
    best_auc = 0
    best_alpha = 0
    
    for alpha in alphas:
        # Combined Z-score
        # score = alpha * z_struct + (1-alpha) * z_dyn
        # Note: If alpha=1, purely structural. If alpha=0, purely dynamical.
        score = alpha * z_struct + (1-alpha) * z_dyn
        
        try:
            current_auc = roc_auc_score(y_true, score)
            aucs.append(current_auc)
            
            if current_auc > best_auc:
                best_auc = current_auc
                best_alpha = alpha
        except:
            aucs.append(0.5)
            
    print(f"Optimization Results:")
    print(f"  Best Alpha (Z-score weighting): {best_alpha:.2f}")
    print(f"  Best AUC: {best_auc:.4f}")
    
    # Plot AUC vs Alpha
    plt.figure()
    plt.plot(alphas, aucs)
    plt.xlabel('Alpha (Weight for Structural Component)')
    plt.ylabel('AUC')
    plt.title('Optimization of Hybrid Weighting')
    plt.axvline(x=best_alpha, color='r', linestyle='--', label=f'Best Alpha={best_alpha:.2f}')
    plt.legend()
    plt.savefig(os.path.join(output_dir, 'alpha_optimization.png'))
    plt.close()
    
    # Plot ROC Comparison
    plt.figure()
    
    # Struct
    fpr_s, tpr_s, _ = roc_curve(y_true, z_struct)
    auc_s = roc_auc_score(y_true, z_struct)
    plt.plot(fpr_s, tpr_s, label=f'Structure Only (AUC={auc_s:.2f})')
    
    # Dyn
    fpr_d, tpr_d, _ = roc_curve(y_true, z_dyn)
    auc_d = roc_auc_score(y_true, z_dyn)
    plt.plot(fpr_d, tpr_d, label=f'Dynamics Only (AUC={auc_d:.2f})')
    
    # Hybrid (Best)
    best_score = best_alpha * z_struct + (1-best_alpha) * z_dyn
    fpr_h, tpr_h, _ = roc_curve(y_true, best_score)
    auc_h = roc_auc_score(y_true, best_score)
    plt.plot(fpr_h, tpr_h, label=f'Hybrid (AUC={auc_h:.2f})', linestyle='--')
    
    plt.plot([0, 1], [0, 1], 'k--')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('ROC Comparison: Structure vs Dynamics')
    plt.legend()
    plt.savefig(os.path.join(output_dir, 'roc_comparison.png'))
    plt.close()
    
    # Also check Raw Structural vs Raw Dynamical AUC
    auc_struct = roc_auc_score(y_true, df['Delta_Struct'])
    auc_dyn = roc_auc_score(y_true, df['Delta_Dyn'])
    print(f"  Pure Structural AUC: {auc_struct:.4f}")
    print(f"  Pure Dynamical AUC: {auc_dyn:.4f}")
    
    return best_alpha, best_auc

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    csv_path = os.path.join(base_dir, "results/level5/hybrid_validation_results.csv")
    output_dir = os.path.join(base_dir, "results/level5")
    optimize_alpha(csv_path, output_dir)
