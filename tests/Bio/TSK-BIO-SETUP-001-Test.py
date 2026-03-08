import unittest
import numpy as np
import json
import os
from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent / "src" / "integration"))

from BioBridge import BioBridge

class TestBioBridge(unittest.TestCase):
    def setUp(self):
        self.bridge = BioBridge()
        self.test_file = "test_network.json"
        
    def test_directory_structure(self):
        """Test if directories are created correctly."""
        self.assertTrue(self.bridge.raw_dir.exists())
        self.assertTrue(self.bridge.processed_dir.exists())
        
    def test_json_roundtrip(self):
        """Test saving and loading data."""
        data = {
            "nodes": ["A", "B"],
            "cm": np.array([[0, 1], [1, 0]]), # Cycle A->B->A
            "logic": {"A": "B", "B": "A"}
        }
        
        # Save
        path = self.bridge.save_network_to_json(data, self.test_file)
        self.assertTrue(path.exists())
        
        # Load manually to verify content
        with open(path, 'r') as f:
            loaded = json.load(f)
            
        self.assertEqual(loaded["nodes"], ["A", "B"])
        self.assertEqual(loaded["cm"], [[0, 1], [1, 0]]) # Numpy array converted to list
        
    def tearDown(self):
        # Clean up
        test_path = self.bridge.processed_dir / self.test_file
        if test_path.exists():
            os.remove(test_path)

if __name__ == "__main__":
    unittest.main()
