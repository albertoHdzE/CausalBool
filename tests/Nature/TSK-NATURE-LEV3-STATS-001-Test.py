import unittest
import numpy as np
import networkx as nx
from scipy.stats import ks_2samp
import os
import sys
import json
from pathlib import Path

# Add src to path
SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from experiments.Null_Generator_HPC import (
    er_edge_shuffle,
    degree_preserving_swap,
    gate_preserving_fanout,
    load_cm,
    PROCESSED_DIR
)

class TestNullModelGenerator(unittest.TestCase):
    
    def setUp(self):
        # Create a simple synthetic network for testing
        # 1 -> 2, 2 -> 3, 3 -> 1 (Cycle) + 1 -> 4
        # In-degrees: 1:1, 2:1, 3:1, 4:1
        # Out-degrees: 1:2, 2:1, 3:1, 4:0
        self.adj = np.array([
            [0, 1, 0, 1],
            [0, 0, 1, 0],
            [1, 0, 0, 0],
            [0, 0, 0, 0]
        ])
        self.in_degs = np.sum(self.adj, axis=0)
        self.out_degs = np.sum(self.adj, axis=1)

    def test_er_shuffle_preserves_edges(self):
        """Test that ER shuffle preserves total number of edges."""
        shuffled = er_edge_shuffle(self.adj, seed=42)
        self.assertEqual(np.sum(shuffled), np.sum(self.adj))
        self.assertFalse(np.array_equal(shuffled, self.adj)) # Should be different

    def test_degree_preserving_null(self):
        """Test that degree-preserving null preserves in/out degree sequences."""
        # For a small graph, it might fail to swap if constrained. 
        # Let's use a slightly larger random graph for robustness.
        G = nx.erdos_renyi_graph(20, 0.3, directed=True, seed=42)
        adj = nx.to_numpy_array(G).astype(int)
        
        in_d_orig = np.sum(adj, axis=0)
        out_d_orig = np.sum(adj, axis=1)
        
        null_adj = degree_preserving_swap(adj, nswap_factor=10, seed=123)
        
        in_d_null = np.sum(null_adj, axis=0)
        out_d_null = np.sum(null_adj, axis=1)
        
        # Exact match required for degree-preserving
        np.testing.assert_array_equal(in_d_null, in_d_orig)
        np.testing.assert_array_equal(out_d_null, out_d_orig)
        
        # KS Test (trivial if identical, but good for formality)
        stat, p = ks_2samp(in_d_orig, in_d_null)
        self.assertGreater(p, 0.99) # Distributions are identical

    def test_gate_preserving_fanout(self):
        """Test that gate-preserving null preserves out-degree (fan-out)."""
        null_adj = gate_preserving_fanout(self.adj, seed=42)
        out_d_null = np.sum(null_adj, axis=1)
        np.testing.assert_array_equal(out_d_null, self.out_degs)
        # In-degree might change
    
    def test_checkpointing_logic(self):
        """Simulate checkpointing by creating a dummy result file."""
        dummy_res = [{"network": "TEST_NET", "z_er": 0.0}]
        res_file = Path("results/bio/null_stats.json")
        
        # Backup existing
        backup = None
        if res_file.exists():
            with open(res_file, "r") as f:
                backup = f.read()
                
        try:
            # Write dummy
            with open(res_file, "w") as f:
                json.dump(dummy_res, f)
            
            # Verify loading
            with open(res_file, "r") as f:
                loaded = json.load(f)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["network"], "TEST_NET")
            
        finally:
            # Restore
            if backup:
                with open(res_file, "w") as f:
                    f.write(backup)
            elif res_file.exists():
                os.remove(res_file)

if __name__ == '__main__':
    unittest.main()
