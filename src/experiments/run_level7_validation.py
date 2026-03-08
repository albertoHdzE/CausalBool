import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc
from datetime import datetime
import json
import glob
import multiprocessing
from functools import partial

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from complexity.Attractor_Classifier import AttractorClassifier
from dynamics.Boolean_Dynamics import BooleanDynamics

def get_essentiality(filename, nodes, manual_metadata, depmap_data):
    """
    Determine essentiality for a network.
    Returns:
        is_essential_map: dict {node: 0/1}
        source: str ('Manual', 'DepMap', 'None')
    """
    # Strategy 1: Manual Metadata
    if filename in manual_metadata:
        ess_set = manual_metadata[filename]
        return {n: (1 if n.upper() in ess_set else 0) for n in nodes}, 'Manual'
        
    # Strategy 2: DepMap
    depmap_hits = 0
    essential_map = {}
    
    for n in nodes:
        n_upper = n.upper()
        if n_upper in depmap_data:
            depmap_hits += 1
            score = depmap_data[n_upper]
            essential_map[n] = 1 if score < -0.8 else 0
        else:
            essential_map[n] = 0
            
    if len(nodes) > 0 and depmap_hits / len(nodes) > 0.3:
        return essential_map, 'DepMap'
        
    return {n: 0 for n in nodes}, 'None'

def process_single_network(filepath, manual_metadata, depmap_data, samples=100, max_steps=200):
    filename = os.path.basename(filepath)
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        nodes = data.get('nodes', [])
        if not nodes:
            return []
            
        # Optimization: Skip large networks
        if len(nodes) > 100:
            return []

        ess_map, source = get_essentiality(filename, nodes, manual_metadata, depmap_data)
        
        wt_sim = BooleanDynamics(data)
        classifier = AttractorClassifier(wt_sim)
        
        try:
            classifier.characterize_wt_attractors(samples=samples, max_steps=max_steps)
        except Exception:
            return []
        
        results = []
        for node in nodes:
            ko_data = json.loads(json.dumps(data))
            ko_data['edges'] = [e for e in ko_data.get('edges', []) if e.get('target') != node]
            ko_data['edges'].append({'source': node, 'target': node, 'type': 'inhibition'})
            
            ko_sim = BooleanDynamics(ko_data)
            
            try:
                metrics = classifier.compute_fidelity(ko_sim, samples=samples, max_steps=max_steps)
                fidelity = metrics['fidelity']
            except Exception:
                fidelity = 0.0
            
            results.append({
                'Network': filename,
                'Gene': node,
                'Fidelity': fidelity,
                'Loss_Fidelity': 1.0 - fidelity,
                'Is_Essential': ess_map.get(node, 0),
                'Source': source
            })
        return results
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return []

def run_experiment():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_dir = os.path.join(base_dir, 'data/bio/processed')
    metadata_path = os.path.join(base_dir, 'data/bio/curated/metadata.csv')
    depmap_path = os.path.join(base_dir, 'data/cancer/depmap_crispr.csv')
    output_dir = os.path.join(base_dir, 'results/level7')
    os.makedirs(output_dir, exist_ok=True)
    
    # Load Data
    manual_metadata = {}
    if os.path.exists(metadata_path):
        df = pd.read_csv(metadata_path)
        for _, row in df.iterrows():
            fname = row['Filename']
            ess_str = row['Essential Genes (comma separated)']
            if pd.isna(ess_str):
                manual_metadata[fname] = set()
            else:
                manual_metadata[fname] = {g.strip().upper() for g in str(ess_str).split(',')}
                
    depmap_data = {}
    if os.path.exists(depmap_path):
        dep_df = pd.read_csv(depmap_path)
        for _, row in dep_df.iterrows():
            depmap_data[str(row['Gene']).upper()] = row['Dependency']

    json_files = glob.glob(os.path.join(data_dir, "*.json"))
    print(f"[{datetime.now()}] Found {len(json_files)} networks. Starting Level 7 Fidelity Validation (Parallel)...")
    
    all_results = []
    
    # Use 75% of CPUs
    num_workers = max(1, int(multiprocessing.cpu_count() * 0.75))
    
    process_func = partial(process_single_network, 
                          manual_metadata=manual_metadata, 
                          depmap_data=depmap_data,
                          samples=100, 
                          max_steps=200)
                          
    with multiprocessing.Pool(processes=num_workers) as pool:
        for i, res in enumerate(pool.imap_unordered(process_func, json_files)):
            if res:
                all_results.extend(res)
            if (i + 1) % 10 == 0:
                print(f"Processed {i+1}/{len(json_files)} networks...")
                
    # Final Save
    df = pd.DataFrame(all_results)
    output_path = os.path.join(output_dir, 'fidelity_validation_results_full.csv')
    df.to_csv(output_path, index=False)
    
    print(f"[{datetime.now()}] Validation Complete. Results saved to {output_path}")
    
    # Basic Stats
    if not df.empty and 'Source' in df.columns:
        valid_df = df[df['Source'].isin(['Manual', 'DepMap'])]
        if not valid_df.empty:
            fpr, tpr, _ = roc_curve(valid_df['Is_Essential'], valid_df['Loss_Fidelity'])
            roc_auc = auc(fpr, tpr)
            print(f"Global AUC (N={valid_df['Network'].nunique()}): {roc_auc:.4f}")
        else:
            print("No valid essentiality data found for AUC calculation.")

if __name__ == "__main__":
    run_experiment()
