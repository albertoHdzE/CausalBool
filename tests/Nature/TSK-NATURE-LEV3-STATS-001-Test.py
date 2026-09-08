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

    def test_separation_is_order_statistics_and_refuses_an_empty_ensemble(self):
        """AUDIT04-F: one definition of the comparison, promoted from a closure.

        Expected values are hand-computed from the definition, not read off the
        function: for x = 10 against nulls {12, 15, 9}, the best null is 9, so
        the gap is 9 - 10 = -1 bit, one null is at least as short, so exceed is
        1/3, and the median null is 12.
        """
        from experiments.Null_Generator_HPC import separation

        s = separation(10.0, [12.0, 15.0, 9.0])
        self.assertAlmostEqual(s['gap_bits'], -1.0)
        self.assertAlmostEqual(s['exceed'], 1 / 3)
        self.assertAlmostEqual(s['best_null'], 9.0)
        self.assertAlmostEqual(s['median_null'], 12.0)

        # Beating every null: gap positive, exceed exactly zero.
        s2 = separation(5.0, [12.0, 15.0, 9.0])
        self.assertAlmostEqual(s2['gap_bits'], 4.0)
        self.assertEqual(s2['exceed'], 0.0)

        with self.assertRaises(ValueError):
            separation(1.0, [])

    def test_summarise_reports_per_measure_and_never_fabricates_a_bdm(self):
        """The monitor's inputs come from order statistics, per measure.

        A network below pybdm's 4x4 floor has NO BDM. The summary must pass
        `None`, because 0.0 is a legitimate gap and the monitor would read it as
        a measured absence of advantage rather than an absent measurement.
        """
        from experiments.SimplicityV2_Nature import summarise

        def rec(gap_i, exc_i, gap_b=None, exc_b=None):
            r = {'D_index_set': 100.0,
                 'index_set': {'gap_bits': gap_i, 'exceed': exc_i,
                               'best_null': 0.0, 'median_null': 120.0},
                 'bdm': None, 'alpha_diff': None}
            if gap_b is not None:
                r['bdm'] = {'gap_bits': gap_b, 'exceed': exc_b,
                            'best_null': 0.0, 'median_null': 0.0}
            return r

        with_bdm = [rec(10.0, 0.0, 4.0, 0.0), rec(2.0, 0.5, -1.0, 0.6),
                    rec(6.0, 0.0, 1.0, 0.0)]
        s = summarise(with_bdm)
        self.assertAlmostEqual(s['gap_bits_deg'], 6.0)     # median of 10, 2, 6
        self.assertAlmostEqual(s['exceed_deg'], 0.0)       # median of 0, .5, 0
        self.assertAlmostEqual(s['gap_bits_bdm'], 1.0)     # median of 4, -1, 1
        self.assertEqual(s['beats_every_null_index'], 2)
        self.assertEqual(s['beats_every_null_bdm'], 2)
        self.assertAlmostEqual(s['aer'], 1.2)              # 120 / 100
        self.assertIsNone(s['scaling_diff'],
                          "the block-size exponent is retired; None, never 0.0")

        no_bdm = summarise([rec(10.0, 0.0), rec(2.0, 0.5)])
        self.assertIsNone(no_bdm['gap_bits_bdm'])
        self.assertIsNone(no_bdm['exceed_bdm'])
        self.assertEqual(no_bdm['beats_every_null_bdm'], 0)

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
