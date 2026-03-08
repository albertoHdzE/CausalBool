
import os
import json
import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from integration.Universal_D_v2_Encoder import UniversalDv2Encoder
from stats.Mutual_Information_Analyzer import MutualInformationAnalyzer

class DepMapValidation:
    def __init__(self, data_dir, depmap_path):
        """
        Initialize the DepMap Validation pipeline.
        
        Args:
            data_dir (str): Directory containing patient networks (JSON).
            depmap_path (str): Path to DepMap CRISPR essentiality data (CSV).
        """
        self.data_dir = data_dir
        self.depmap_path = depmap_path
        self.depmap_data = self._load_depmap()
        
    def _load_depmap(self):
        """
        Load DepMap data. 
        Expects CSV with columns 'Gene' and 'Dependency'.
        Dependency Score < -1 implies Essentiality.
        """
        if not os.path.exists(self.depmap_path):
            print(f"Warning: DepMap file {self.depmap_path} not found.")
            return pd.DataFrame(columns=["Gene", "Dependency"])
        return pd.read_csv(self.depmap_path)

    def compute_d_v2(self, cm):
        """Compute D_v2 for an adjacency matrix."""
        if cm is None or len(cm) == 0:
            return 0
        encoder = UniversalDv2Encoder(cm)
        result = encoder.compute()
        return result["dv2"]

    def analyze_single_network(self, network_path):
        """
        Perform in-silico knockout for all genes in a single network
        and compute Delta D (Impact).
        """
        with open(network_path, 'r') as f:
            net = json.load(f)
            
        nodes = net.get("nodes", [])
        cm = np.array(net.get("cm", []))
        
        if len(cm) == 0:
            return {}
            
        # Baseline D
        d_baseline = self.compute_d_v2(cm.tolist())
        
        results = {}
        
        for i, gene in enumerate(nodes):
            # In-silico Knockout: Remove node i
            # We create a sub-matrix by deleting row i and col i
            cm_ko = np.delete(np.delete(cm, i, axis=0), i, axis=1)
            
            d_ko = self.compute_d_v2(cm_ko.tolist())
            
            # Delta D = D_baseline - D_knockout
            # Positive Delta D means the node contributed structural information (Complexity dropped)
            # Negative Delta D means the node was "noise" (Complexity increased)
            delta_d = d_baseline - d_ko
            
            # Get DepMap score if available
            dep_score = self.depmap_data[self.depmap_data["Gene"] == gene]["Dependency"].mean()
            if pd.isna(dep_score):
                dep_score = 0 # or NaN
                
            results[gene] = {
                "delta_d": delta_d,
                "dependency": dep_score
            }
            
        return results

    def run_cohort_analysis(self, n_patients=None):
        """
        Run knockout analysis on all tumor networks in data_dir.
        """
        print(f"[{datetime.now()}] Starting DepMap Validation...")
        
        files = [f for f in os.listdir(self.data_dir) if f.endswith("_Tumor.json")]
        if n_patients:
            files = files[:n_patients]
            
        aggregated_results = {} # Gene -> [Delta_D values across patients]
        
        for f in files:
            path = os.path.join(self.data_dir, f)
            res = self.analyze_single_network(path)
            
            for gene, metrics in res.items():
                if gene not in aggregated_results:
                    aggregated_results[gene] = {"delta_ds": [], "dep_score": metrics["dependency"]}
                aggregated_results[gene]["delta_ds"].append(metrics["delta_d"])
                
        # Summarize
        summary = []
        for gene, data in aggregated_results.items():
            mean_delta_d = np.mean(data["delta_ds"])
            summary.append({
                "Gene": gene,
                "Mean_Delta_D": mean_delta_d,
                "Dependency": data["dep_score"]
            })
            
        return pd.DataFrame(summary)

    def compute_correlation(self, results):
        """
        Compute correlation and Mutual Information between Delta D and Dependency Score.
        Args:
            results: DataFrame or Dict
        """
        if isinstance(results, dict):
            # Convert dict from analyze_single_network to DF-like lists
            delta_ds = [v["delta_d"] for v in results.values()]
            deps = [v["dependency"] for v in results.values()]
        else:
            delta_ds = results["Mean_Delta_D"]
            deps = results["Dependency"]
            
        # Remove NaNs
        valid_indices = [i for i in range(len(deps)) if not np.isnan(deps[i])]
        if len(valid_indices) < 3:
            return {'rho': 0.0, 'pval': 1.0, 'mi_bits': 0.0, 'mi_interpretation': "Insufficient Data"}
            
        delta_ds = [delta_ds[i] for i in valid_indices]
        deps = [deps[i] for i in valid_indices]
        
        # Pearson
        corr, pval = stats.pearsonr(delta_ds, deps)
        
        # Mutual Information
        mi_res = MutualInformationAnalyzer.compute_mutual_information(delta_ds, deps, discrete_y=False)
        
        return {
            'rho': corr,
            'pval': pval,
            'mi_bits': mi_res['MI_bits'],
            'mi_interpretation': mi_res['interpretation']
        }

if __name__ == "__main__":
    # Example Usage
    DATA_DIR = "data/cancer/patients"
    DEPMAP_PATH = "data/cancer/depmap_crispr.csv"
    
    # Check if DepMap exists, if not create dummy
    if not os.path.exists(DEPMAP_PATH):
        print("DepMap file not found. Generating synthetic DepMap data for testing...")
        # Create dummy based on genes in a random file
        sample_file = [f for f in os.listdir(DATA_DIR) if f.endswith(".json")][0]
        with open(os.path.join(DATA_DIR, sample_file)) as f:
            genes = json.load(f)["nodes"]
            
        df = pd.DataFrame({
            "Gene": genes,
            "Dependency": np.random.normal(-0.5, 1.0, len(genes)) # Mix of essential (-1.5) and non-essential (0)
        })
        # Force some essential genes
        essentials = ["EGFR", "GRB2", "RAS", "MEK", "ERK"]
        for g in essentials:
            if g in genes:
                df.loc[df["Gene"] == g, "Dependency"] = -2.0 # Highly essential
                
        df.to_csv(DEPMAP_PATH, index=False)
        
    validator = DepMapValidation(DATA_DIR, DEPMAP_PATH)
    cohort_results = validator.run_cohort_analysis(n_patients=20) # Analyze 20 patients
    
    # Save
    cohort_results.to_csv("results/cancer/depmap_validation.csv", index=False)
    
    # Correlation
    stats_res = validator.compute_correlation(cohort_results)
    print(f"Global Correlation (Delta D vs Dependency): r={stats_res['rho']:.2f}, p={stats_res['pval']:.2e}")
    print(f"Mutual Information: {stats_res['mi_bits']:.2f} bits ({stats_res['mi_interpretation']})")
    
    # Save Stats
    stats_path = "results/cancer/depmap_stats.json"
    with open(stats_path, 'w') as f:
        json.dump(stats_res, f, indent=4)
    print(f"Stats saved to {stats_path}")
    
    # Expect negative correlation: High Delta D (Important Structure) <-> Low Dependency Score (Essential)
    # Wait, Dependency Score is usually "Effect Size", where -2 is lethal.
    # So "Essential" = Negative Score.
    # "Important Structure" = High Delta D (Removing it destroys structure).
    # So High Delta D should map to Negative Score.
    # Correlation should be NEGATIVE.
