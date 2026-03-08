import numpy as np
import collections
from .Basin_Entropy import BasinEntropyEstimator

class AttractorClassifier:
    """
    Classifies attractors and computes Fidelity metrics.
    Compares Knockout (KO) basins to Wild Type (WT) basins.
    """
    
    def __init__(self, wt_simulator):
        self.wt_sim = wt_simulator
        self.wt_attractors = None # Set of attractor signatures
        
    def characterize_wt_attractors(self, samples=500, max_steps=1000, window_size=50):
        """
        Identify WT attractors using Monte Carlo sampling.
        Stores them as a set of unique signatures.
        """
        estimator = BasinEntropyEstimator(self.wt_sim)
        res = estimator.estimate_entropy(samples=samples, max_steps=max_steps, window_size=window_size)
        
        # Store attractors (dict mapping hash -> representative states)
        # We need the hashes (keys) to identify them later.
        self.wt_attractors = set(res['attractors'].keys())
        self.wt_basin_sizes = res['basin_sizes'] # For reference
        return res
        
    def compute_fidelity(self, ko_simulator, samples=500, max_steps=1000, window_size=50):
        """
        Compute Fidelity of KO network to WT attractors.
        Fidelity = Sum(P_KO(a)) for all a in A_WT.
        
        Args:
            ko_simulator: Simulator for the KO network.
        """
        if self.wt_attractors is None:
            raise ValueError("WT attractors not characterized. Run characterize_wt_attractors first.")
            
        estimator = BasinEntropyEstimator(ko_simulator)
        res = estimator.estimate_entropy(samples=samples, max_steps=max_steps, window_size=window_size)
        
        ko_attractors = res['attractors'] # dict: hash -> states
        ko_counts = res['attractor_counts'] # dict: hash -> count
        
        fidelity_count = 0
        total_samples = samples
        
        # Check each KO attractor against WT set
        # Note: Exact match of hashes implies exact match of state sets.
        # This is strict. A KO might slightly perturb an attractor (e.g., 1 bit flip).
        # For Level 7, we start with EXACT match (Semantic Stability).
        # If an essential gene is lost, we expect the attractor to be lost or changed.
        
        for attr_hash, count in ko_counts.items():
            if attr_hash in self.wt_attractors:
                fidelity_count += count
                
        fidelity = fidelity_count / total_samples
        
        return {
            'fidelity': fidelity,
            'wt_attractors_count': len(self.wt_attractors),
            'ko_attractors_count': len(ko_attractors),
            'shared_attractors_count': len(set(ko_attractors.keys()) & self.wt_attractors)
        }
