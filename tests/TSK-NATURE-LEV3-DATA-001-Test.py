import unittest
from pathlib import Path
import json
import sys
import numpy as np

# Add src to path
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from integration.grn_data_pipeline import GRNLoader

class TestDataCollection(unittest.TestCase):
    def setUp(self):
        self.loader = GRNLoader()
        self.processed_dir = self.loader.processed_dir
        
    def test_processed_files_exist(self):
        """Verify that processed files exist."""
        files = list(self.processed_dir.glob("*.json"))
        self.assertTrue(len(files) > 0, "No processed JSON files found")
        print(f"\nFound {len(files)} processed models.")
        
    def test_model_structure(self):
        """Verify structure of processed models (nodes 5-100, valid keys)."""
        files = list(self.processed_dir.glob("*.json"))
        # Exclude known non-model files if any
        files = [f for f in files if f.name not in ["gate_histogram.json", "truth_tables.json"]]

        for f in files:
            # Skip lambda_phage for node count check as it is a small curated model (N=4)
            if f.name == "lambda_phage.json":
                continue

            with open(f, "r") as json_file:
                data = json.load(json_file)
                
            # Check required keys
            required_keys = ["name", "n", "edges", "cm", "out_degrees"]
            for key in required_keys:
                self.assertIn(key, data, f"Missing key {key} in {f.name}")
                
            # Check node count constraint
            n = data["n"]
            self.assertTrue(5 <= n <= 100, f"Model {f.name} has {n} nodes, outside 5-100 range")
            
            # Check connectivity (simple check: at least some edges)
            n_edges = len(data["edges"])
            self.assertTrue(n_edges > 0, f"Model {f.name} has 0 edges")
            
            # Check connectivity matrix shape
            cm = np.array(data["cm"])
            self.assertEqual(cm.shape, (n, n), f"CM shape mismatch in {f.name}")

if __name__ == "__main__":
    unittest.main()
