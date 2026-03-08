import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import roc_curve, auc
import os

# Set style
sns.set_style("whitegrid")
plt.rcParams.update({'font.size': 12, 'figure.figsize': (8, 6)})

# Paths
BASE_DIR = "/Users/alberto/Documents/projects/CausalBoolIntegration"
DATA_DIR = os.path.join(BASE_DIR, "data/bio/processed")
RESULTS_DIR = os.path.join(BASE_DIR, "results/bio")
FIGURES_DIR = os.path.join(BASE_DIR, "doc/finalpaper/figures")

os.makedirs(FIGURES_DIR, exist_ok=True)

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

# --- Figure 1: Gate Distribution ---
def plot_gate_distribution():
    print("Generating Figure 1: Gate Distribution...")
    data = load_json(os.path.join(DATA_DIR, "gate_histogram.json"))
    
    # Process Global Data
    global_counts = data['global']
    gates = sorted(global_counts.keys(), key=lambda x: global_counts[x], reverse=True)
    counts = [global_counts[g] for g in gates]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(x=gates, y=counts, hue=gates, palette="viridis", ax=ax, legend=False)
    ax.set_title("Global Logic Gate Distribution in Biological Networks")
    ax.set_ylabel("Count")
    ax.set_xlabel("Gate Type")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "mechanism_behaviour.pdf"))
    plt.close()

# --- Figure 2: Algorithmic Simplicity (D_bio vs D_rand) ---
def plot_simplicity():
    print("Generating Figure 2: Algorithmic Simplicity...")
    data = load_json(os.path.join(RESULTS_DIR, "metricks/D_metrics_refined_null.json"))
    
    networks = []
    d_bio = []
    d_rand = []
    d_rand_err = []
    
    # Formatting names
    name_map = {
        "lambda_phage": "Lambda Phage",
        "lac_operon": "Lac Operon",
        "yeast_cell_cycle": "Yeast Cell Cycle",
        "tcell_activation": "T-Cell"
    }
    
    for net, stats in data.items():
        if net in name_map:
            networks.append(name_map[net])
            d_bio.append(stats['D_bio'])
            d_rand.append(stats['D_rand_mean_refined'])
            d_rand_err.append(stats['D_rand_std_refined'])
            
    x = np.arange(len(networks))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(8, 6))
    rects1 = ax.bar(x - width/2, d_bio, width, label='$D_{bio}$', color='#2ecc71')
    rects2 = ax.bar(x + width/2, d_rand, width, yerr=d_rand_err, label='$D_{rand}$', color='#95a5a6', capsize=5)
    
    ax.set_ylabel('Mechanistic Description Length (bits)')
    ax.set_title('Algorithmic Simplicity: Bio vs Random')
    ax.set_xticks(x)
    ax.set_xticklabels(networks)
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "simplicity.pdf"))
    plt.close()

# --- Figure 3: Essentiality ROC & Figure 4: Decoupling ---
def plot_essentiality_and_decoupling():
    print("Generating Figure 3 (ROC) and Figure 4 (Decoupling)...")
    data = load_json(os.path.join(RESULTS_DIR, "knockouts/bdm_knockouts.json"))
    df = pd.DataFrame(data)
    
    # Fix potential string essentiality
    df['Essentiality'] = df['Essentiality'].apply(lambda x: int(x))
    
    # --- ROC Curve (Fig 3) ---
    fpr, tpr, _ = roc_curve(df['Essentiality'], df['DeltaD'])
    roc_auc = auc(fpr, tpr)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Panel A: ROC
    ax1.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {roc_auc:.2f})')
    ax1.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    ax1.set_xlim([0.0, 1.0])
    ax1.set_ylim([0.0, 1.05])
    ax1.set_xlabel('False Positive Rate')
    ax1.set_ylabel('True Positive Rate')
    ax1.set_title('Essentiality Prediction via $\Delta D$')
    ax1.legend(loc="lower right")
    
    # Panel B: Distribution
    # Use hue for palette to avoid warning, set legend=False
    sns.boxplot(x='Essentiality', y='DeltaD', hue='Essentiality', data=df, ax=ax2, palette={0: "#3498db", 1: "#e74c3c"}, legend=False)
    ax2.set_xticklabels(['Non-Essential', 'Essential'])
    ax2.set_ylabel('Mechanistic Information Loss ($\Delta D$)')
    ax2.set_title('Algorithmic Load by Essentiality')
    
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "essentiality_roc.pdf"))
    plt.close()
    
    # --- Decoupling (Fig 4) ---
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Scatter plot
    sns.scatterplot(
        data=df, 
        x='DeltaBDM', 
        y='DeltaD', 
        hue='Essentiality', 
        style='Network',
        palette={0: "#3498db", 1: "#e74c3c"},
        s=100,
        ax=ax
    )
    
    # Add labels for top hits
    for i, row in df.iterrows():
        if row['DeltaD'] > 12 or row['DeltaBDM'] > 1: # Label outliers/significant points
            ax.text(row['DeltaBDM']+0.1, row['DeltaD'], row['Gene'], fontsize=9)
            
    ax.set_xlabel('Behavioural Change ($\Delta$BDM)')
    ax.set_ylabel('Mechanistic Change ($\Delta D$)')
    ax.set_title('Decoupling of Mechanism and Behaviour')
    
    # Custom legend
    handles, labels = ax.get_legend_handles_labels()
    # Replace 0/1 with text
    new_labels = ['Non-Essential', 'Essential'] if '0' in labels else labels
    # This is a bit tricky with seaborn legends, simplifying:
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "decoupling.pdf"))
    plt.close()

# --- Figure 5: Phase Transition ---
def plot_phase_transition():
    print("Generating Figure 5: Phase Transition...")
    data = load_json(os.path.join(RESULTS_DIR, "phase_transition/phase_transition.json"))
    df = pd.DataFrame(data)
    
    # Group by pXOR
    grouped = df.groupby('pXOR').agg({
        'D': ['mean', 'std'],
        'BDM': ['mean', 'std']
    }).reset_index()
    
    pXOR = grouped['pXOR']
    D_mean = grouped['D']['mean']
    D_std = grouped['D']['std']
    BDM_mean = grouped['BDM']['mean']
    BDM_std = grouped['BDM']['std']
    
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    color = 'tab:blue'
    ax1.set_xlabel('Proportion of XOR Gates ($p_{XOR}$)')
    ax1.set_ylabel('Mechanistic Complexity ($D$)', color=color)
    ax1.plot(pXOR, D_mean, color=color, marker='o', label='$D$')
    ax1.fill_between(pXOR, D_mean - D_std, D_mean + D_std, alpha=0.2, color=color)
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.set_ylim(80, 120)
    
    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
    
    color = 'tab:red'
    ax2.set_ylabel('Behavioural Complexity (BDM)', color=color)  # we already handled the x-label with ax1
    ax2.plot(pXOR, BDM_mean, color=color, marker='s', linestyle='--', label='BDM')
    ax2.fill_between(pXOR, BDM_mean - BDM_std, BDM_mean + BDM_std, alpha=0.2, color=color)
    ax2.tick_params(axis='y', labelcolor=color)
    ax2.set_yscale('log')
    
    plt.title('Algorithmic Phase Transition at Edge of Chaos')
    fig.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "phase_transition.pdf"))
    plt.close()

if __name__ == "__main__":
    plot_gate_distribution()
    plot_simplicity()
    plot_essentiality_and_decoupling()
    plot_phase_transition()
    print("All figures generated successfully.")
