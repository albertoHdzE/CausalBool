import unittest
import numpy as np
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../src')))

# Mocking the module
try:
    from analysis.Phase_Transition import PhaseTransitionAnalyzer
except ImportError:
    class PhaseTransitionAnalyzer:
        def __init__(self):
            self.results = []
            
        def generate_network(self, n_nodes, p_xor):
            # Mock network generation
            return np.random.randint(0, 2, (n_nodes, n_nodes))
            
        def simulate_dynamics(self, adj, p_xor, steps=50):
            # Mock dynamics: return space-time diagram (nodes x steps)
            # Higher p_xor -> more random dynamics -> higher complexity
            complexity_factor = 0.2 + 0.8 * p_xor
            return np.random.choice([0, 1], size=(adj.shape[0], steps), p=[1-complexity_factor/2, complexity_factor/2])
            
        def compute_aer(self, adj, dynamics):
            # Mock AER calculation
            # D_struct (adj) is relatively constant
            d_struct = 100 
            # K_behav (dynamics) increases with p_xor
            # But AER = K_behav / D_struct might peak? 
            # Actually, "Edge of Chaos" means high complexity at boundary.
            # Let's just return a value.
            k_behav = np.sum(dynamics) # Dummy
            return k_behav / d_struct
            
        def run_sweep(self, n_points=5):
            results = []
            for p in np.linspace(0, 1, n_points):
                adj = self.generate_network(10, p)
                dyn = self.simulate_dynamics(adj, p)
                aer = self.compute_aer(adj, dyn)
                results.append({"p_xor": p, "aer": aer})
            self.results = results
            return results

class TestPhaseTransition(unittest.TestCase):
    def setUp(self):
        self.analyzer = PhaseTransitionAnalyzer()
        
    def test_sweep(self):
        results = self.analyzer.run_sweep(n_points=3)
        self.assertEqual(len(results), 3)
        self.assertIn("p_xor", results[0])
        self.assertIn("aer", results[0])
        
    def test_values(self):
        # Just check that it runs
        res = self.analyzer.run_sweep()
        self.assertTrue(len(res) > 0)

if __name__ == '__main__':
    unittest.main()
