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
        """Round-trip through the module's OWN save/load, on a temporary path.

        AUDIT04-F. This test used to open `results/bio/null_stats.json` -- the
        real, tracked artefact carrying 231 measured records -- overwrite it with
        a dummy, and restore it in a `finally`. Two defects. It put a published
        artefact one interrupted run away from being replaced by a stub; and it
        reimplemented `json.dump`/`json.load` rather than calling
        `save_results`/`load_existing_results`, so the functions it purported to
        test were never executed.
        """
        import tempfile
        import experiments.Null_Generator_HPC as ng

        dummy = [{"network": "TEST_NET", "D_bio": 1.0, "measure": "index_set_program_length"}]
        with tempfile.TemporaryDirectory() as tmp:
            old_dir, old_file = ng.RESULTS_DIR, ng.NULL_STATS_FILE
            try:
                ng.RESULTS_DIR = Path(tmp) / "bio"
                ng.NULL_STATS_FILE = ng.RESULTS_DIR / "null_stats.json"
                self.assertEqual(ng.load_existing_results(), [],
                                 "an absent checkpoint must read as empty, not raise")
                ng.save_results(dummy)
                loaded = ng.load_existing_results()
                self.assertEqual(loaded, dummy)
                # A corrupt checkpoint must not abort a 24-minute run.
                ng.NULL_STATS_FILE.write_text("{ not json")
                self.assertEqual(ng.load_existing_results(), [])
            finally:
                ng.RESULTS_DIR, ng.NULL_STATS_FILE = old_dir, old_file
        self.assertTrue(old_file == ng.NULL_STATS_FILE,
                        "the module's real path must be restored")

    def test_both_measures_are_computed_for_the_same_matrix(self):
        """AUDIT04-F: the null experiment scores every matrix twice, by name.

        The author's directive of 2026-09-07 names two comparison measures. They
        are reported side by side and never merged (decision #96 forbids folding
        them into one number), so this asserts that both are present, that they
        are different numbers, and that BDM refuses rather than returning zero
        below its 4x4 partition floor.
        """
        from experiments.Null_Generator_HPC import compute_both

        both = compute_both(self.adj)
        self.assertIn("index_set", both)
        self.assertIn("bdm", both)
        self.assertGreater(both["index_set"], 0.0)
        self.assertIsNotNone(both["bdm"])
        self.assertNotAlmostEqual(both["index_set"], both["bdm"], places=6,
                                  msg="two measures reporting the same number "
                                      "would make reporting both pointless")

        tiny = np.array([[0, 1], [1, 0]])
        self.assertIsNone(compute_both(tiny)["bdm"],
                          "below the 4x4 floor BDM is UNMEASURED, never 0 bits")

    def test_the_nulls_preserve_what_each_claims_to_preserve(self):
        """Each null is only a control if its invariant holds.

        Stated per null, because they fail differently and a null that quietly
        changed the edge count would make every gap in bits meaningless.
        """
        e = int(self.adj.sum())
        self.assertEqual(int(er_edge_shuffle(self.adj, seed=1).sum()), e)
        deg = degree_preserving_swap(self.adj, nswap_factor=10, seed=1)
        self.assertTrue((deg.sum(axis=0) == self.in_degs).all(),
                        "degree_preserving_swap must preserve IN-degree; the "
                        "schema-length invariance argument depends on it")
        fan = gate_preserving_fanout(self.adj, seed=1)
        self.assertTrue((fan.sum(axis=1) == self.out_degs).all(),
                        "gate_preserving_fanout must preserve out-degree")

if __name__ == '__main__':
    unittest.main()
