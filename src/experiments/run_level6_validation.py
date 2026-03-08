import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc
from datetime import datetime
import json

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from integration.Basin_Encoder import BasinEncoder
from analysis.Hybrid_Essentiality_Validator import HybridEssentialityValidator # We can reuse logic or copy

class BasinValidator:
    def __init__(self, data_dir, metadata_path):
        self.data_dir = data_dir
        self.metadata_path = metadata_path
        
    def load_metadata(self):
        return pd.read_csv(self.metadata_path)
        
    def validate_network(self, filename, essential_genes_str, samples=500, max_steps=1000):
        # Load network
        path = os.path.join(self.data_dir, filename)
        with open(path, 'r') as f:
            data = json.load(f)
            
        nodes = data.get('nodes', [])
        
        # Parse essential genes
        if pd.isna(essential_genes_str):
            ess_set = set()
        else:
            ess_set = {g.strip() for g in str(essential_genes_str).split(',')}
            
        # Compute Baseline Entropy
        encoder = BasinEncoder(data)
        base_metrics = encoder.compute_basin_metrics(samples=samples, max_steps=max_steps)
        base_h = base_metrics['h_basin']
        
        results = []
        
        for i, node in enumerate(nodes):
            # Create Knockout Network
            # We can do this efficiently by modifying the rules in memory or passing a "fixed_nodes" dict to simulator
            # But our Simulator currently takes rules from constructor.
            # Easiest way: Modify data dict and re-instantiate Encoder.
            
            # Deep copy data to avoid side effects
            ko_data = json.loads(json.dumps(data))
            
            # Find the node index? No, need to modify logic.
            # In our format, we can just remove all incoming edges to the node
            # AND remove it from all source lists?
            # Or simpler: Add a self-loop that forces 0?
            # Or modify logic rules directly if we had them.
            # Given our BooleanDynamics parses 'edges', we can remove all edges where target is the node
            # and ensure it has no activators.
            
            # Actually, `HybridEssentialityValidator` likely had a helper for this. Let's check or re-implement.
            # Re-implementation:
            # Set node to constant 0.
            # In `BooleanDynamics._parse_rules`, if a node has no inputs, it stays constant.
            # So if we remove all edges targeting this node, and ensure initial state is 0...
            # But initial state is random.
            # So we need to enforce the node to be 0.
            
            # Better approach:
            # Modify `BooleanDynamics` to accept `fixed_nodes={index: value}`.
            # But we can't modify `BooleanDynamics` easily inside the loop without re-instantiating.
            # So we modify the input data.
            
            # Remove edges where target == node
            ko_data['edges'] = [e for e in ko_data.get('edges', []) if e.get('target') != node]
            # And we need to make sure it doesn't stay at 1 if initialized at 1.
            # If no edges, it preserves state.
            # To force 0: Add a fictitious inhibitor from a node that is always 1? Complex.
            # To force 0: Add a self-inhibition? node -| node.
            # If only inhibitor, it goes to 0.
            ko_data['edges'].append({'source': node, 'target': node, 'type': 'inhibition'})
            
            ko_encoder = BasinEncoder(ko_data)
            ko_metrics = ko_encoder.compute_basin_metrics(samples=samples, max_steps=max_steps)
            ko_h = ko_metrics['h_basin']
            
            delta_h = base_h - ko_h
            
            # Label
            is_ess = 0
            if node in ess_set:
                is_ess = 1
            else:
                for e in ess_set:
                    if e.lower() == node.lower():
                        is_ess = 1
                        break
                        
            results.append({
                'Network': filename,
                'Gene': node,
                'Base_H': base_h,
                'KO_H': ko_h,
                'Delta_H': delta_h,
                'Is_Essential': is_ess
            })
            
        return results

def run_experiment():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_dir = os.path.join(base_dir, 'data/bio/processed')
    metadata_path = os.path.join(base_dir, 'data/bio/curated/metadata.csv')
    output_dir = os.path.join(base_dir, 'results/level6')
    os.makedirs(output_dir, exist_ok=True)
    
    validator = BasinValidator(data_dir, metadata_path)
    metadata = validator.load_metadata()
    
    all_results = []
    
    print(f"[{datetime.now()}] Starting Level 6 Basin Validation...")
    
    for idx, row in metadata.iterrows():
        filename = row['Filename']
        ess_genes = row['Essential Genes (comma separated)']
        print(f"Processing {filename}...")
        
        if not os.path.exists(os.path.join(data_dir, filename)):
            print(f"  Skipping (not found)")
            continue
            
        try:
            # Use fewer samples for speed in this run, but enough for estimation
            res = validator.validate_network(filename, ess_genes, samples=200, max_steps=500)
            all_results.extend(res)
        except Exception as e:
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            
    # Save results
    df = pd.DataFrame(all_results)
    csv_path = os.path.join(output_dir, 'basin_validation_results.csv')
    df.to_csv(csv_path, index=False)
    print(f"Results saved to {csv_path}")
    
    if len(df) == 0:
        return
        
    # Analysis
    y_true = df['Is_Essential']
    y_scores = df['Delta_H'] # We expect Essential -> High Impact -> High Delta?
    # Or maybe Essential -> Collapse of Complexity -> Positive Delta?
    # Or Essential -> Loss of Stability -> Negative Delta?
    # Let's assume magnitude or positive delta.
    
    if y_true.sum() == 0:
        print("No essential genes found.")
        return
        
    fpr, tpr, _ = roc_curve(y_true, y_scores)
    roc_auc = auc(fpr, tpr)
    print(f"Global AUC (Delta H): {roc_auc:.4f}")
    
    # Check absolute delta too
    fpr_abs, tpr_abs, _ = roc_curve(y_true, y_scores.abs())
    roc_auc_abs = auc(fpr_abs, tpr_abs)
    print(f"Global AUC (|Delta H|): {roc_auc_abs:.4f}")
    
    # Plot
    plt.figure()
    plt.plot(fpr, tpr, label=f'Signed Delta H (AUC={roc_auc:.2f})')
    plt.plot(fpr_abs, tpr_abs, label=f'Abs Delta H (AUC={roc_auc_abs:.2f})')
    plt.plot([0, 1], [0, 1], 'k--')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('ROC: Basin Entropy Essentiality Prediction')
    plt.legend()
    plt.savefig(os.path.join(output_dir, 'roc_basin.png'))
    plt.close()

if __name__ == '__main__':
    run_experiment()
