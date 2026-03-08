import os
import sys
import json
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from integration.Hybrid_Encoder import HybridEncoder

class HybridEssentialityValidator:
    def __init__(self, data_dir, metadata_path):
        self.data_dir = data_dir
        self.metadata_path = metadata_path
        
    def load_metadata(self):
        if not os.path.exists(self.metadata_path):
            raise FileNotFoundError(f"Metadata file not found: {self.metadata_path}")
        return pd.read_csv(self.metadata_path)
        
    def validate_network(self, filename, essential_genes_str, alpha=0.5, beta=0.5, steps=100):
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            return []
            
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        nodes = data.get('nodes', [])
        # Parse essential genes (handle whitespace)
        if pd.isna(essential_genes_str):
            ess_set = set()
        else:
            ess_set = {g.strip() for g in str(essential_genes_str).split(',')}
            
        # Initialize Hybrid Encoder
        encoder = HybridEncoder(data)
        
        # Compute Baseline Hybrid Complexity
        # Note: HybridEncoder computes D_struct and D_dyn.
        # D_struct is expensive? No, N=10-20 is fast.
        # D_dyn takes simulation.
        
        # Baseline
        base_res = encoder.compute_hybrid_complexity(alpha=alpha, beta=beta, steps=steps, trials=5)
        base_h = base_res['d_hybrid']
        
        results = []
        
        # Knockout Analysis
        # HybridEncoder needs to support "virtual knockout" without reloading everything?
        # Current HybridEncoder takes data in __init__.
        # So we need to create new HybridEncoder for each knockout.
        # This is slow but cleaner.
        
        for i, node in enumerate(nodes):
            # Create KO data
            ko_data = self._create_ko_data(data, i)
            
            ko_encoder = HybridEncoder(ko_data)
            ko_res = ko_encoder.compute_hybrid_complexity(alpha=alpha, beta=beta, steps=steps, trials=5)
            ko_h = ko_res['d_hybrid']
            
            delta_h = base_h - ko_h
            delta_struct = base_res['d_struct'] - ko_res['d_struct']
            delta_dyn = base_res['d_dyn'] - ko_res['d_dyn']
            
            # Label
            # Try exact match, then case insensitive
            is_ess = 0
            if node in ess_set:
                is_ess = 1
            else:
                # Fallback: check if node upper/lower matches any essential gene
                for e in ess_set:
                    if e.lower() == node.lower():
                        is_ess = 1
                        break
                        
            results.append({
                'Network': filename,
                'Gene': node,
                'Delta_H': delta_h,
                'Delta_Struct': delta_struct,
                'Delta_Dyn': delta_dyn,
                'Is_Essential': is_ess,
                'D_Struct_Base': base_res['d_struct'],
                'D_Dyn_Base': base_res['d_dyn']
            })
            
        return results

    def _create_ko_data(self, original_data, node_index):
        """Create a deep copy of data with node_index removed."""
        # Simple approach: Remove node from list, remove edges involving it.
        # But indices shift!
        # And 'cm' needs update if present.
        
        new_data = {}
        nodes = original_data.get('nodes', [])
        target_node = nodes[node_index]
        
        # New nodes list
        new_nodes = [n for j, n in enumerate(nodes) if j != node_index]
        new_data['nodes'] = new_nodes
        
        # Update CM if exists
        if 'cm' in original_data:
            cm = np.array(original_data['cm'])
            if cm.shape[0] == len(nodes):
                new_cm = np.delete(np.delete(cm, node_index, axis=0), node_index, axis=1)
                new_data['cm'] = new_cm.tolist()
                
        # Update edges
        if 'edges' in original_data:
            new_edges = []
            for edge in original_data['edges']:
                s = edge.get('source')
                t = edge.get('target')
                if s != target_node and t != target_node:
                    new_edges.append(edge)
            new_data['edges'] = new_edges
            
        return new_data

