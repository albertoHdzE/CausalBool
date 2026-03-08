import os
import sys
import json
import numpy as np
import pandas as pd
import networkx as nx
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, precision_recall_curve, auc
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from integration.Universal_D_v2_Encoder import UniversalDv2Encoder

class EssentialityPredictor:
    def __init__(self, data_dir, metadata_path):
        self.data_dir = data_dir
        self.metadata_path = metadata_path
        self.results_df = None
        
    def load_metadata(self):
        if not os.path.exists(self.metadata_path):
            raise FileNotFoundError(f"Metadata file not found: {self.metadata_path}")
        return pd.read_csv(self.metadata_path)
        
    def compute_d_v2(self, cm):
        """Compute D_v2 for an adjacency matrix."""
        if cm is None or len(cm) == 0:
            return 0
        encoder = UniversalDv2Encoder(cm)
        result = encoder.compute()
        return result["dv2"]

    def process_network(self, network_file, essential_genes_str):
        filepath = os.path.join(self.data_dir, network_file)
        if not os.path.exists(filepath):
            print(f"Warning: Network file {filepath} not found. Skipping.")
            return []
            
        with open(filepath, 'r') as f:
            net_data = json.load(f)
            
        nodes = net_data.get("nodes", [])
        cm = np.array(net_data.get("cm", []))
        
        if len(cm) == 0:
            return []
            
        # Build NetworkX graph for centrality
        G = nx.from_numpy_array(cm, create_using=nx.DiGraph)
        
        # Centrality metrics
        degree_dict = dict(G.degree())
        try:
            betweenness_dict = nx.betweenness_centrality(G)
        except:
            betweenness_dict = {i: 0 for i in range(len(nodes))}
            
        # Parse essential genes
        essential_genes = [g.strip() for g in str(essential_genes_str).split(',')]
        
        # Baseline D_v2
        d_baseline = self.compute_d_v2(cm.tolist())
        
        network_results = []
        
        for i, gene_name in enumerate(nodes):
            # In-silico Knockout
            cm_ko = np.delete(np.delete(cm, i, axis=0), i, axis=1)
            d_ko = self.compute_d_v2(cm_ko.tolist())
            delta_d = d_baseline - d_ko
            
            # Label
            is_essential = 1 if gene_name in essential_genes else 0
            
            network_results.append({
                "Network": network_file,
                "Gene": gene_name,
                "Delta_D": delta_d,
                "Degree": degree_dict.get(i, 0),
                "Betweenness": betweenness_dict.get(i, 0),
                "Is_Essential": is_essential
            })
            
        return network_results

    def build_dataset(self):
        meta = self.load_metadata()
        all_results = []
        
        print(f"Processing {len(meta)} networks...")
        for _, row in meta.iterrows():
            net_file = row['Filename']
            ess_genes = row['Essential Genes (comma separated)']
            print(f"  - {net_file}")
            res = self.process_network(net_file, ess_genes)
            all_results.extend(res)
            
        self.results_df = pd.DataFrame(all_results)
        return self.results_df
        
    def run_cv(self, k=5):
        if self.results_df is None or self.results_df.empty:
            print("No data to run CV.")
            return 0.0
            
        X = self.results_df[['Delta_D', 'Degree', 'Betweenness']]
        y = self.results_df['Is_Essential']
        
        # Check if we have enough positive samples
        if y.sum() < k:
            print(f"Warning: Only {y.sum()} essential genes. Cannot run {k}-fold CV.")
            return 0.0
            
        # Classifier: Random Forest is usually robust
        clf = RandomForestClassifier(n_estimators=100, random_state=42)
        
        cv = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)
        
        aucs = cross_val_score(clf, X, y, cv=cv, scoring='roc_auc')
        mean_auc = np.mean(aucs)
        
        print(f"5-Fold CV AUC: {mean_auc:.4f} (+/- {np.std(aucs):.4f})")
        
        # Also compare to baselines
        # Degree only
        degree_auc = roc_auc_score(y, X['Degree'])
        print(f"Degree Centrality AUC: {degree_auc:.4f}")
        
        # Delta D only
        deltad_auc = roc_auc_score(y, X['Delta_D'])
        print(f"Delta D AUC: {deltad_auc:.4f}")
        
        return mean_auc

if __name__ == "__main__":
    # Config
    DATA_DIR = "data/bio/curated" # Assuming JSONs are here alongside metadata
    METADATA_PATH = "data/bio/curated/metadata.csv"
    
    # Run
    predictor = EssentialityPredictor(DATA_DIR, METADATA_PATH)
    
    # If data/bio/curated doesn't contain the JSONs (they might be in data/bio/processed), 
    # we might need to check.
    # The metadata.csv filename column usually assumes a relative path or just filename.
    # Let's check if the JSONs are in `data/bio/curated` or `data/bio/processed`.
    
    if not os.path.exists(os.path.join(DATA_DIR, "egfr_signaling.json")):
        # Try processed directory
        DATA_DIR = "data/bio/processed"
        predictor.data_dir = DATA_DIR
        
    print(f"Using Data Directory: {DATA_DIR}")
    
    df = predictor.build_dataset()
    if not df.empty:
        df.to_csv("results/bio/essentiality_prediction_dataset.csv", index=False)
        predictor.run_cv()
