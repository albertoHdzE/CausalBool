import json
import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# Setup
sns.set_style("whitegrid")
plt.rcParams.update({'font.size': 12, 'figure.figsize': (10, 6)})

# Determine base directory relative to this script
# Script is in doc/finalpaper/scripts
# Root is ../../../
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
RESULTS_PATH = os.path.join(BASE_DIR, "results/bio/simplicity_v2_real.json")
FIGURES_DIR = os.path.join(BASE_DIR, "doc/finalpaper/figures")

os.makedirs(FIGURES_DIR, exist_ok=True)

def load_data():
    with open(RESULTS_PATH, 'r') as f:
        data = json.load(f)
    return pd.DataFrame(data)

def plot_z_scores(df):
    print("Generating Universality Z-Scores Plot...")
    
    # Sort by Z-score
    df_sorted = df.sort_values('z_score')
    
    # Clean network names for display
    df_sorted['display_name'] = df_sorted['network'].str.replace('_', ' ').str.title()
    
    # Color mapping based on Z-score sign
    # Green for simple (negative), Red for complex (positive)
    colors = ['#2ecc71' if z < 0 else '#e74c3c' for z in df_sorted['z_score']]
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(df_sorted['display_name'], df_sorted['z_score'], color=colors)
    
    plt.axhline(0, color='black', linewidth=0.8)
    plt.axhline(-2, color='gray', linestyle='--', linewidth=0.8, label='Significance Threshold ($Z=-2$)')
    # plt.axhline(2, color='gray', linestyle='--', linewidth=0.8)
    
    plt.ylabel('Simplicity Z-Score ($Z$)')
    plt.title('Universality of Algorithmic Simplicity in Biological Networks')
    plt.xticks(rotation=45, ha='right')
    plt.legend()
    
    # Add value labels
    for bar in bars:
        height = bar.get_height()
        xy = (bar.get_x() + bar.get_width() / 2, height)
        xytext = (0, 3) if height > 0 else (0, -12)
        plt.annotate(f'{height:.1f}', xy=xy, xytext=xytext,
                     textcoords="offset points", ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "universality_zscores.pdf"))
    plt.close()

def plot_mechanism_vs_behaviour(df):
    print("Generating Mechanism vs Behaviour Plot...")
    
    plt.figure(figsize=(10, 8))
    
    # Clean network names
    df['display_name'] = df['network'].str.replace('_', ' ').str.title()
    
    # Map categories to colors/markers
    # Ensure categories match data
    unique_cats = df['category'].unique()
    palette = sns.color_palette("bright", len(unique_cats))
    
    sns.scatterplot(
        data=df,
        x='avg_bdm',
        y='D_v2',
        hue='category',
        style='category',
        s=200,
        palette='deep'
    )
    
    # Label points
    for i, row in df.iterrows():
        plt.text(row['avg_bdm']+0.1, row['D_v2'], row['display_name'], fontsize=9)
        
    plt.xlabel('Behavioural Complexity ($K_{BDM}$)')
    plt.ylabel('Structural Description Length ($D_{v2}$)')
    plt.title('The Mechanism-Behaviour Phase Space')
    
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "mechanism_vs_behaviour_nature.pdf"))
    plt.close()

if __name__ == "__main__":
    if not os.path.exists(RESULTS_PATH):
        print(f"Error: Results file not found at {RESULTS_PATH}")
    else:
        df = load_data()
        plot_z_scores(df)
        plot_mechanism_vs_behaviour(df)
        print(f"Figures generated in {FIGURES_DIR}")
