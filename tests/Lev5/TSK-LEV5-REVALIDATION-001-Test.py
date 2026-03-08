import unittest
import os
import sys
import pandas as pd
import numpy as np

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from analysis.Hybrid_Essentiality_Validator import HybridEssentialityValidator

class TestLev5Revalidation(unittest.TestCase):
    
    def setUp(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), '../../data/bio/processed')
        self.metadata_path = os.path.join(os.path.dirname(__file__), '../../data/bio/curated/metadata.csv')
        
        if not os.path.exists(self.metadata_path):
            self.skipTest("Metadata not found")
            
        self.validator = HybridEssentialityValidator(self.data_dir, self.metadata_path)

    def test_single_network_validation(self):
        """TSK-LEV5-REVALIDATION-001: Validate on Mammalian Cell Cycle"""
        # Metadata entry: 
        # Mammalian Cell Cycle,ginsim_2006-mammal-cell-cycle_boolean_cell_cycle.json,...,"RB1,E2F1,CycE",...
        
        filename = "ginsim_2006-mammal-cell-cycle_boolean_cell_cycle.json"
        essential_genes = "RB1,E2F1,CycE" 
        
        # Run validation with small steps for speed
        results = self.validator.validate_network(filename, essential_genes, alpha=0.5, beta=0.5, steps=50)
        
        self.assertGreater(len(results), 0)
        
        # Check structure
        first = results[0]
        self.assertIn('Gene', first)
        self.assertIn('Delta_H', first)
        self.assertIn('Is_Essential', first)
        
        # Check if essential genes were identified (even if 0 found due to naming, the logic ran)
        # Note: RB1 vs Rb, E2F1 vs E2F, CycE vs CycE.
        # CycE should be essential.
        
        ess_found = [r for r in results if r['Is_Essential'] == 1]
        print(f"Essential genes found in test: {[r['Gene'] for r in ess_found]}")
        
        # We expect at least CycE to be matched if case-insensitive logic works
        # CycE in JSON is "CycE". In CSV "CycE". Match!
        self.assertTrue(len(ess_found) > 0, "No essential genes matched in test network")

if __name__ == '__main__':
    unittest.main()
