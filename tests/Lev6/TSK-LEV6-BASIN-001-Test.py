import unittest
import numpy as np
import os
import sys
import json

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from dynamics.Boolean_Dynamics import BooleanDynamics
from complexity.Basin_Entropy import BasinEntropyEstimator
from integration.Basin_Encoder import BasinEncoder

def load_mammalian_cycle():
    # Helper for testing
    path = os.path.join(os.path.dirname(__file__), '../../data/bio/processed/ginsim_2006-mammal-cell-cycle_boolean_cell_cycle.json')
    with open(path, 'r') as f:
        return json.load(f)

class TestLevel6Basin(unittest.TestCase):
    
    def setUp(self):
        # Load real data
        self.data = load_mammalian_cycle()
        self.sim = BooleanDynamics(self.data)
        
    def test_asynchronous_update(self):
        """Test if async update changes state differently than sync"""
        # Find a state that is NOT a fixed point in sync
        # If it's a fixed point, async won't change it either.
        initial_state = np.random.randint(0, 2, size=self.sim.n)
        
        # Async step
        async_next = self.sim.step_async(initial_state)
        
        # Check if only one node changed (or zero if it was already stable)
        diff = np.abs(initial_state - async_next)
        num_changes = np.sum(diff)
        
        # In async, at most 1 node changes per step (relative to previous state)
        # Note: step_async handles batch size, so returns (Batch, N) if input is (Batch, N)
        # If input is (N,), it might return (1, N) based on implementation, let's check.
        # Boolean_Dynamics implementation: if input ndim=1, it expands, but returns squeezed?
        # No, step_async returns next_state_batch which is (Batch, N).
        
        if async_next.ndim == 2 and initial_state.ndim == 1:
             diff = np.abs(initial_state - async_next[0])
             num_changes = np.sum(diff)
        
        self.assertLessEqual(num_changes, 1)
        
    def test_basin_entropy_calculation(self):
        """Test Basin Entropy estimator on real network"""
        estimator = BasinEntropyEstimator(self.sim)
        
        # Run small sample for speed
        res = estimator.estimate_entropy(samples=50, max_steps=100, window_size=10)
        
        print(f"\nBasin Entropy Test Results:")
        print(f"  Entropy: {res['entropy']:.4f}")
        print(f"  Num Attractors: {res['num_attractors']}")
        print(f"  Basin Sizes: {res['basin_sizes']}")
        
        self.assertGreaterEqual(res['entropy'], 0.0)
        self.assertGreater(res['num_attractors'], 0)
        
    def test_basin_encoder(self):
        """Test BasinEncoder wrapper"""
        encoder = BasinEncoder(self.data)
        metrics = encoder.compute_basin_metrics(samples=20, max_steps=50)
        
        self.assertIn('h_basin', metrics)
        self.assertIn('p_max', metrics)

if __name__ == '__main__':
    unittest.main()
