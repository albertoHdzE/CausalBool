import numpy as np
import sys
import os

# Ensure src is in path for absolute imports if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dynamics.Boolean_Dynamics import BooleanDynamics
from complexity.Basin_Entropy import BasinEntropyEstimator

class BasinEncoder:
    """
    Computes Basin Entropy and related landscape metrics.
    Acts as the primary encoder for Level 6.
    """
    
    def __init__(self, network_data):
        self.network_data = network_data
        self.sim = BooleanDynamics(network_data)
        self.estimator = BasinEntropyEstimator(self.sim)
        
        # Cache
        self.results = None
        
    def compute_basin_metrics(self, samples=500, max_steps=1000, window_size=50):
        """
        Compute Basin Entropy.
        
        Args:
            samples: Number of MC samples (default 500 for speed in high-throughput).
            max_steps: Steps to reach attractor.
            
        Returns:
            dict: {'h_basin': float, 'num_attractors': int, 'p_max': float}
        """
        if self.results is not None:
            return self.results
            
        res = self.estimator.estimate_entropy(samples=samples, max_steps=max_steps, window_size=window_size)
        
        basin_sizes = res['basin_sizes']
        p_max = basin_sizes[0] if basin_sizes else 0.0
        
        self.results = {
            'h_basin': res['entropy'],
            'num_attractors': res['num_attractors'],
            'p_max': p_max,
            'details': res
        }
        
        return self.results
