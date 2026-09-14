import math
import unittest
import numpy as np
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from integration.HierarchyEncoder import HierarchyEncoder

class TestHierarchyEncoder(unittest.TestCase):
    def test_pure_dag(self):
        """A -> B -> C: zero feedback edges, and a NON-ZERO description length.

        AUDIT04-F. This test asserted ``hierarchy_cost == 0`` and measured
        4.754887502163468 bits, and it was carried in quarantine as an open
        question: real defect, or mis-stated invariant?

        It is a MIS-STATED INVARIANT, and the mistake is a category error rather
        than an arithmetic one. ``feedback_edges`` is a COUNT and is correctly
        zero for an acyclic graph. ``hierarchy_cost`` is a DESCRIPTION LENGTH --
        the bits needed to write this hierarchy down. A cost of zero would say
        the decoder can reconstruct a three-node chain from nothing, and no
        object with structure costs nothing to transmit. Asserting zero here
        would have made the encoder wrong in order to make the test pass.

        The expected value is DERIVED from the cost model rather than copied
        from the output (the AUDIT04 rule for every floor and expectation):

            layer assignment : n * log2(num_layers) = 3 * log2(3) = 4.754887...
            edge encoding    : per ordered layer pair, log2(C(|Li|*|Lj|, k_ij)).
                               Every layer holds ONE node here, so each block has
                               max_edges = 1 and k in {0, 1}; C(1,0) = C(1,1) = 1
                               and log2(1) = 0. The whole edge term vanishes.

        So the total is exactly 3*log2(3), and it is 3*log2(3) because each of
        the three nodes must be told which of the three layers it belongs to.
        """
        cm = np.zeros((3, 3), dtype=int)
        cm[0, 1] = 1 # A->B
        cm[1, 2] = 1 # B->C

        encoder = HierarchyEncoder(cm)
        results = encoder.run()

        self.assertEqual(len(results['feedback_edges']), 0)

        expected = 3 * math.log2(3)   # n * log2(num_layers); edge term is zero
        self.assertAlmostEqual(results['hierarchy_cost'], expected, places=12)
        self.assertGreater(results['hierarchy_cost'], 0.0,
                           "a description length of a structured object cannot "
                           "be zero; that would mean it transmits for free")

    def test_cycle(self):
        """
        A -> B -> A
        Both edges are within the same SCC, so both are 'lateral' (layer i -> layer i).
        Should count as feedback/violation.
        """
        cm = np.zeros((2, 2), dtype=int)
        cm[0, 1] = 1
        cm[1, 0] = 1
        
        encoder = HierarchyEncoder(cm)
        results = encoder.run()
        
        # Both edges are intra-layer
        self.assertEqual(len(results['feedback_edges']), 2)
        self.assertGreater(results['hierarchy_cost'], 0)

    def test_mixed(self):
        """
        A -> B (cycle B<->C) -> D
        A (0)
        B (1) <-> C (2)
        C (2) -> D (3)
        
        SCCs: {A}, {B,C}, {D}
        Layers: 0, 1, 2
        Edges:
        A->B (Forward)
        B->C (Lateral)
        C->B (Lateral)
        C->D (Forward)
        
        Feedback: 2 (B->C, C->B)
        """
        cm = np.zeros((4, 4), dtype=int)
        cm[0, 1] = 1
        cm[1, 2] = 1
        cm[2, 1] = 1
        cm[2, 3] = 1
        
        encoder = HierarchyEncoder(cm)
        results = encoder.run()
        
        self.assertEqual(len(results['feedback_edges']), 2)

if __name__ == '__main__':
    unittest.main()
