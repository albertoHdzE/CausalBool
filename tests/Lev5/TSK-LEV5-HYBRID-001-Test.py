import unittest
import numpy as np
import os
import sys
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from integration.Hybrid_Encoder import HybridEncoder

class TestLev5Hybrid(unittest.TestCase):
    
    def setUp(self):
        # Path to real biological network
        self.net_path = os.path.join(os.path.dirname(__file__), '../../data/bio/processed/ginsim_2006-mammal-cell-cycle_boolean_cell_cycle.json')
        if not os.path.exists(self.net_path):
            self.skipTest("Real network file not found")
            
        with open(self.net_path, 'r') as f:
            self.net_data = json.load(f)

    def test_hybrid_complexity_components(self):
        """TSK-LEV5-HYBRID-001: Component Verification"""
        encoder = HybridEncoder(self.net_data)
        
        # 1. Pure Structural (Alpha=1, Beta=0)
        res_struct = encoder.compute_hybrid_complexity(alpha=1.0, beta=0.0, steps=100, trials=1)
        self.assertGreater(res_struct['d_struct'], 0)
        self.assertAlmostEqual(res_struct['d_hybrid'], res_struct['d_struct'])
        
        # 2. Pure Dynamical (Alpha=0, Beta=1)
        res_dyn = encoder.compute_hybrid_complexity(alpha=0.0, beta=1.0, steps=100, trials=1)
        self.assertGreater(res_dyn['d_dyn'], 0)
        self.assertAlmostEqual(res_dyn['d_hybrid'], res_dyn['d_dyn'])
        
        # 3. Hybrid (Alpha=0.5, Beta=0.5)
        res_hybrid = encoder.compute_hybrid_complexity(alpha=0.5, beta=0.5, steps=100, trials=1)
        expected = 0.5 * res_struct['d_struct'] + 0.5 * res_dyn['d_dyn']
        self.assertAlmostEqual(res_hybrid['d_hybrid'], expected)
        
    def test_caching(self):
        """TSK-LEV5-HYBRID-001: Caching Mechanism"""
        encoder = HybridEncoder(self.net_data)
        
        # First call computes
        res1 = encoder.compute_hybrid_complexity(alpha=1.0, beta=0.0, steps=10, trials=1)
        
        # Modify cached value manually to verify caching works (hacky but effective test)
        encoder.d_struct = 9999.0
        
        # Second call should use cached value
        res2 = encoder.compute_hybrid_complexity(alpha=1.0, beta=0.0, steps=10, trials=1)
        self.assertEqual(res2['d_struct'], 9999.0)

if __name__ == '__main__':
    unittest.main()
