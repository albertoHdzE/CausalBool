import unittest
import numpy as np
import os
import sys
import json

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from dynamics.Boolean_Dynamics import BooleanDynamics
from complexity.Attractor_Classifier import AttractorClassifier

def load_mammalian_cycle():
    # Helper for testing
    path = os.path.join(os.path.dirname(__file__), '../../data/bio/processed/ginsim_2006-mammal-cell-cycle_boolean_cell_cycle.json')
    with open(path, 'r') as f:
        return json.load(f)

class TestLevel7Fidelity(unittest.TestCase):
    
    def setUp(self):
        # Load real data
        self.data = load_mammalian_cycle()
        self.wt_sim = BooleanDynamics(self.data)
        self.classifier = AttractorClassifier(self.wt_sim)
        
    def test_fidelity_workflow(self):
        """Test the full fidelity workflow: characterize WT -> compute KO fidelity"""
        
        # 1. Characterize WT (small sample for speed)
        print("\nCharacterizing WT Attractors...")
        self.classifier.characterize_wt_attractors(samples=50, max_steps=100)
        
        # Verify attractors found
        self.assertGreater(len(self.classifier.wt_attractors), 0)
        
        # 2. Simulate "KO" (Mock: same network, should have Fidelity ~ 1.0)
        # Note: Due to stochastic sampling, it might not be exactly 1.0 if we miss rare attractors
        # But for prominent ones it should be high.
        print("Computing Fidelity for Self (Control)...")
        res = self.classifier.compute_fidelity(self.wt_sim, samples=50, max_steps=100)
        
        print(f"Fidelity (Self): {res['fidelity']:.4f}")
        # Should be high (allow some sampling noise)
        self.assertGreater(res['fidelity'], 0.5)
        
        # 3. Simulate Actual KO (Mock: Random Network)
        # Or just use a random dynamics object
        random_data = {'nodes': self.data['nodes'], 'edges': []} # Disconnected
        ko_sim = BooleanDynamics(random_data)
        
        print("Computing Fidelity for Random KO...")
        res_ko = self.classifier.compute_fidelity(ko_sim, samples=50, max_steps=100)
        print(f"Fidelity (Random): {res_ko['fidelity']:.4f}")
        
        # Should be lower than self
        self.assertLess(res_ko['fidelity'], res['fidelity'])

if __name__ == '__main__':
    unittest.main()
