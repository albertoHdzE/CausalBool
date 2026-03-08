
import unittest
import os
import json
import numpy as np
import pandas as pd
import shutil
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from analysis.DepMap_Validation import DepMapValidation

class TestDepMapValidation(unittest.TestCase):
    def setUp(self):
        self.test_dir = "tests/temp_depmap"
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Create a dummy network
        self.net_path = os.path.join(self.test_dir, "test_net.json")
        net = {
            "nodes": ["A", "B", "C"],
            "cm": [[0, 1, 0], [0, 0, 1], [1, 0, 0]], # Loop A->B->C->A
            "logic": {"A": "C", "B": "A", "C": "B"}
        }
        with open(self.net_path, 'w') as f:
            json.dump(net, f)
            
        # Create dummy DepMap data
        self.depmap_path = os.path.join(self.test_dir, "depmap.csv")
        depmap_data = pd.DataFrame({
            "Gene": ["A", "B", "C"],
            "Dependency": [-1.5, -0.2, -1.0] # A is essential, B is not, C is moderate
        })
        depmap_data.to_csv(self.depmap_path, index=False)
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    def test_knockout_impact(self):
        validator = DepMapValidation(self.test_dir, self.depmap_path)
        
        # Calculate impact for the test network
        # Passing list of networks or directory? Let's assume directory or single file helper
        results = validator.analyze_single_network(self.net_path)
        
        # Check structure of results
        self.assertIn("A", results)
        self.assertIn("delta_d", results["A"])
        
        # A (Essential) should have high Delta D (removing it breaks the loop)
        # B (Non-essential in DepMap, but structurally identical here)
        # Note: In this simple ring, all nodes are structurally identical. 
        # So Delta D should be equal. 
        # This test mainly checks pipeline mechanics, not biological truth.
        
        self.assertEqual(results["A"]["delta_d"], results["B"]["delta_d"])
        
    def test_correlation(self):
        # Create results where Delta D matches Dependency
        results = {
            "A": {"delta_d": 10.0, "dependency": -2.0},
            "B": {"delta_d": 1.0, "dependency": -0.1},
            "C": {"delta_d": 5.0, "dependency": -1.0}
        }
        
        validator = DepMapValidation(self.test_dir, self.depmap_path)
        corr, pval = validator.compute_correlation(results)
        
        # High Delta D (10) corresponds to Low Score (-2.0) -> Strong Negative Correlation
        # Wait, usually Dependency Score < -1 means Essential.
        # So Higher Delta D (Structural Loss) should correlate with More Negative Score.
        # Thus Correlation should be Negative.
        
        self.assertTrue(corr < -0.8)

if __name__ == '__main__':
    unittest.main()
