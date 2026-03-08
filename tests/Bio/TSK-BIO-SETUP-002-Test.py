
import unittest
import numpy as np
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from integration.BDM_Wrapper import BDMWrapper

class TestBDMIntegration(unittest.TestCase):
    
    def setUp(self):
        self.wrapper = BDMWrapper()
        
    def test_zero_matrix_complexity(self):
        """Test that a zero matrix has low complexity."""
        zero_matrix = np.zeros((10, 10), dtype=int)
        result = self.wrapper.compute_bdm(zero_matrix)
        
        print(f"\n[Test] Zero Matrix BDM: {result['bdm_value']}")
        self.assertIsInstance(result["bdm_value"], float)
        self.assertGreater(result["bdm_value"], 0)
        
    def test_random_matrix_complexity(self):
        """Test that a random matrix has higher complexity than a zero matrix."""
        # Fix seed for reproducibility
        np.random.seed(42)
        
        zero_matrix = np.zeros((10, 10), dtype=int)
        random_matrix = np.random.randint(0, 2, (10, 10))
        
        res_zero = self.wrapper.compute_bdm(zero_matrix)
        res_random = self.wrapper.compute_bdm(random_matrix)
        
        print(f"[Test] Random Matrix BDM: {res_random['bdm_value']}")
        print(f"[Test] Delta (Random - Zero): {res_random['bdm_value'] - res_zero['bdm_value']}")
        
        # BDM of random should be significantly higher
        self.assertGreater(res_random["bdm_value"], res_zero["bdm_value"])
        
    def test_structure_preservation(self):
        """Test that BDM respects structure (identity matrix vs random)."""
        identity = np.eye(10, dtype=int)
        random_matrix = np.random.randint(0, 2, (10, 10))
        
        res_id = self.wrapper.compute_bdm(identity)
        res_rand = self.wrapper.compute_bdm(random_matrix)
        
        print(f"[Test] Identity Matrix BDM: {res_id['bdm_value']}")
        
        # Identity is simple, but more complex than all zeros. 
        # Random should still be more complex than Identity.
        self.assertGreater(res_rand["bdm_value"], res_id["bdm_value"])

if __name__ == '__main__':
    unittest.main()
