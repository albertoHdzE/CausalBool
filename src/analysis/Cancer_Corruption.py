
import json
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from integration.Universal_D_v2_Encoder import UniversalDv2Encoder

# Configuration
DATA_DIR = "data/cancer/patients"
METADATA_PATH = "data/cancer/clinical_metadata.csv"
OUTPUT_DIR = "results/cancer"
FIGURE_DIR = "doc/finalpaper/figures"

# Ensure directories
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(FIGURE_DIR, exist_ok=True)

def load_network(path):
    with open(path, 'r') as f:
        return json.load(f)

def compute_d_v2(json_data):
    cm = json_data.get("cm")
    if not cm:
        return None
    encoder = UniversalDv2Encoder(cm)
    result = encoder.compute()
    return result["dv2"]

def main():
    print(f"[{datetime.now()}] Starting Cancer Corruption Analysis...")
    
    # Load Metadata
    df = pd.read_csv(METADATA_PATH)
    results = []
    
    print(f"[{datetime.now()}] Processing {len(df)} patients...")
    
    for _, row in df.iterrows():
        pid = row["PatientID"]
        normal_path = os.path.join(DATA_DIR, f"{pid}_Normal.json")
        tumor_path = os.path.join(DATA_DIR, f"{pid}_Tumor.json")
        
        if not os.path.exists(normal_path) or not os.path.exists(tumor_path):
            print(f"Warning: Missing files for {pid}")
            continue
            
        normal_data = load_network(normal_path)
        tumor_data = load_network(tumor_path)
        
        d_normal = compute_d_v2(normal_data)
        d_tumor = compute_d_v2(tumor_data)
        
        delta_d = d_tumor - d_normal
        
        results.append({
            "PatientID": pid,
            "Subtype": row["Subtype"],
            "SurvivalDays": row["SurvivalDays"],
            "MutationCount": row["MutationCount"],
            "D_normal": d_normal,
            "D_tumor": d_tumor,
            "Delta_D": delta_d
        })
        
    results_df = pd.DataFrame(results)
    
    # Save Results
    results_path = os.path.join(OUTPUT_DIR, "corruption_metrics.csv")
    results_df.to_csv(results_path, index=False)
    print(f"[{datetime.now()}] Results saved to {results_path}")
    
    # Statistical Analysis
    # 1. Paired t-test
    t_stat, p_val = stats.ttest_rel(results_df["D_normal"], results_df["D_tumor"])
    print(f"\nStatistical Summary:")
    print(f"  Mean D_normal: {results_df['D_normal'].mean():.2f}")
    print(f"  Mean D_tumor:  {results_df['D_tumor'].mean():.2f}")
    print(f"  Mean Delta_D:  {results_df['Delta_D'].mean():.2f}")
    print(f"  Paired t-test: t={t_stat:.2f}, p={p_val:.2e}")
    
    # 2. Correlation with Survival
    corr, p_corr = stats.pearsonr(results_df["Delta_D"], results_df["SurvivalDays"])
    print(f"  Correlation (Delta_D vs Survival): r={corr:.2f}, p={p_corr:.2e}")
    
    # Plotting
    # Plot 1: Distribution of Delta D
    plt.figure(figsize=(10, 6))
    sns.histplot(results_df["Delta_D"], kde=True, color="firebrick")
    plt.axvline(0, color='k', linestyle='--')
    plt.title("Distribution of Algorithmic Corruption ($\Delta D$)")
    plt.xlabel("$\Delta D = D_{tumor} - D_{normal}$ (Bits)")
    plt.savefig(os.path.join(FIGURE_DIR, "cancer_delta_d_dist.png"))
    
    # Plot 2: Delta D vs Survival
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=results_df, x="Delta_D", y="SurvivalDays", hue="Subtype", palette="viridis")
    sns.regplot(data=results_df, x="Delta_D", y="SurvivalDays", scatter=False, color="gray")
    plt.title(f"Algorithmic Corruption vs Survival (r={corr:.2f})")
    plt.xlabel("$\Delta D$ (Structural Information Loss)")
    plt.ylabel("Survival (Days)")
    plt.savefig(os.path.join(FIGURE_DIR, "cancer_survival_corr.png"))
    
    print(f"[{datetime.now()}] Plots saved to {FIGURE_DIR}")

if __name__ == "__main__":
    main()
