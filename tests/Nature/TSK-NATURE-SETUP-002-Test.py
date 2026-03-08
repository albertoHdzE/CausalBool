import unittest
import numpy as np
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from integration.HierarchyEncoder import HierarchyEncoder

class TestHierarchyEncoder(unittest.TestCase):
    def test_pure_dag(self):
        """
        A -> B -> C
        Should be 0 feedback edges.
        """
        cm = np.zeros((3, 3), dtype=int)
        cm[0, 1] = 1 # A->B
        cm[1, 2] = 1 # B->C
        
        encoder = HierarchyEncoder(cm)
        results = encoder.run()
        
        self.assertEqual(len(results['feedback_edges']), 0)
        self.assertEqual(results['hierarchy_cost'], 0)

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
