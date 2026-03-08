
import unittest
import os
import json
import shutil
import numpy as np
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from data.cancer_network_builder import CancerNetworkBuilder

class TestCancerNetworkBuilder(unittest.TestCase):
    def setUp(self):
        self.test_dir = "tests/temp_cancer_data"
        os.makedirs(self.test_dir, exist_ok=True)
        self.base_net_path = os.path.join(self.test_dir, "base.json")
        
        # Create a dummy base network
        base_net = {
            "nodes": ["A", "B", "C"],
            "logic": {"A": "B", "B": "C", "C": "A"},
            "cm": [[0, 0, 1], [1, 0, 0], [0, 1, 0]] # A<-C, B<-A, C<-B
        }
        with open(self.base_net_path, 'w') as f:
            json.dump(base_net, f)
            
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    def test_network_generation(self):
        builder = CancerNetworkBuilder(self.base_net_path, self.test_dir)
        
        # Test internal mutation logic directly
        # GoF on A
        mutations = {"A": "GoF"}
        tumor_net = builder._create_network("TEST-001", "Tumor", mutations)
        
        # Check Logic Change
        self.assertEqual(tumor_net["logic"]["A"], "1")
        
        # Check Structural Change (CM)
        # Node A is index 0. Row 0 should be all 0s.
        cm = np.array(tumor_net["cm"])
        self.assertTrue(np.all(cm[0, :] == 0))
        
        # Node B (Index 1) should still have input from A (Index 0) -> cm[1,0] == 1
        self.assertEqual(cm[1, 0], 1)
        
    def test_cohort_generation(self):
        metadata_path = os.path.join(self.test_dir, "clinical_metadata.csv")
        builder = CancerNetworkBuilder(self.base_net_path, self.test_dir, metadata_path)
        builder.drivers = {"oncogenes": ["A"], "suppressors": ["B"]} # Mock drivers
        
        # Generate small cohort
        builder.generate_patient_cohort(n_patients=5)
        
        # Check files exist
        for i in range(5):
            pid = f"TCGA-BR-{i:04d}"
            self.assertTrue(os.path.exists(os.path.join(self.test_dir, f"{pid}_Normal.json")))
            self.assertTrue(os.path.exists(os.path.join(self.test_dir, f"{pid}_Tumor.json")))
            
        # Check metadata
        self.assertTrue(os.path.exists(metadata_path))

if __name__ == '__main__':
    unittest.main()
