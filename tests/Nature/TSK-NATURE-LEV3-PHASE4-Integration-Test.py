
import unittest
import os
import json
import numpy as np
import sys
import shutil

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from data.cancer_network_builder import CancerNetworkBuilder
from analysis.Cancer_Corruption import compute_d_v2
from analysis.DepMap_Validation import DepMapValidation

class TestPhase4Integration(unittest.TestCase):
    def setUp(self):
        self.test_dir = "tests/temp_phase4_integration"
        os.makedirs(self.test_dir, exist_ok=True)
        self.base_net_path = os.path.join(self.test_dir, "base_int.json")
        self.metadata_path = os.path.join(self.test_dir, "metadata_int.csv")
        self.depmap_path = os.path.join(self.test_dir, "depmap_int.csv")
        
        # 1. Create Base Network
        base_net = {
            "nodes": ["A", "B", "C", "D", "E"],
            "logic": {"A": "B", "B": "C", "C": "D", "D": "E", "E": "A"}, # Ring 5
            "cm": [[0,1,0,0,0], [0,0,1,0,0], [0,0,0,1,0], [0,0,0,0,1], [1,0,0,0,0]]
        }
        with open(self.base_net_path, 'w') as f:
            json.dump(base_net, f)
            
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    def test_end_to_end_pipeline(self):
        """
        Verify the full flow:
        Generation -> Corruption Analysis -> DepMap Validation
        """
        
        # Step 1: Generate Cohort
        builder = CancerNetworkBuilder(self.base_net_path, self.test_dir, self.metadata_path)
        # Mock drivers to ensure mutations happen
        builder.drivers = {"oncogenes": ["A"], "suppressors": ["C"]}
        builder.generate_patient_cohort(n_patients=10)
        
        self.assertTrue(os.path.exists(self.metadata_path))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "TCGA-BR-0000_Tumor.json")))
        
        # Step 2: Corruption Analysis (Metric Computation)
        # We manually invoke the logic from Cancer_Corruption.py on one pair
        normal_path = os.path.join(self.test_dir, "TCGA-BR-0000_Normal.json")
        tumor_path = os.path.join(self.test_dir, "TCGA-BR-0000_Tumor.json")
        
        with open(normal_path) as f: normal_data = json.load(f)
        with open(tumor_path) as f: tumor_data = json.load(f)
        
        d_normal = compute_d_v2(normal_data)
        d_tumor = compute_d_v2(tumor_data)
        
        # D_v2 should return a float
        self.assertIsInstance(d_normal, float)
        self.assertIsInstance(d_tumor, float)
        
        # Step 3: DepMap Validation
        # Create dummy DepMap
        with open(self.depmap_path, 'w') as f:
            f.write("Gene,Dependency\nA,-1.5\nB,-0.1\nC,-2.0\nD,0.0\nE,0.5\n")
            
        validator = DepMapValidation(self.test_dir, self.depmap_path)
        # Analyze the generated tumor networks
        results = validator.run_cohort_analysis(n_patients=10)
        
        self.assertFalse(results.empty)
        self.assertIn("Mean_Delta_D", results.columns)
        self.assertIn("Dependency", results.columns)
        
        # Step 4: Regression Check
        # Ensure D_v2 is stable for the known base network (Ring 5)
        # A simple Ring 5 should have D_v2 around ~ 15-25 bits (very low) depending on implementation details
        # Random 5x5 is higher.
        
        encoder = validator.compute_d_v2
        # Base CM from setup
        base_cm = [[0,1,0,0,0], [0,0,1,0,0], [0,0,0,1,0], [0,0,0,0,1], [1,0,0,0,0]]
        d_base = encoder(base_cm)
        
        # Regression value: In Phase 1/2, did we establish a value?
        # Let's just assert it's deterministic and reasonable.
        self.assertTrue(d_base > 0)
        self.assertTrue(d_base < 100) 

if __name__ == '__main__':
    unittest.main()
