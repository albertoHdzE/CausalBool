import unittest
import numpy as np
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from integration.MotifEncoder import MotifEncoder

class TestMotifEncoder(unittest.TestCase):
    def test_ffl_detection(self):
        """
        Test detection of a single Feed-Forward Loop (FFL).
        A -> B
        B -> C
        A -> C
        """
        # Adjacency matrix (4 nodes) to ensure non-zero location cost
        # 0: A, 1: B, 2: C, 3: D (isolated)
        # A->B (0,1), B->C (1,2), A->C (0,2)
        cm = np.zeros((4, 4), dtype=int)
        cm[0, 1] = 1
        cm[1, 2] = 1
        cm[0, 2] = 1
        
        encoder = MotifEncoder(cm)
        results = encoder.run()
        
        # Check if FFL is detected
        self.assertIn('FFL', results['instances'])
        self.assertEqual(len(results['instances']['FFL']), 1)
        self.assertEqual(results['instances']['FFL'][0], (0, 1, 2))
        
        # Check cost
        self.assertGreater(results['motif_cost'], 0)
        print(f"FFL Graph Cost: {results['motif_cost']} bits")

    def test_feedback_loop_detection(self):
        """
        Test detection of a 3-node Feedback Loop.
        A -> B -> C -> A
        """
        cm = np.zeros((3, 3), dtype=int)
        cm[0, 1] = 1
        cm[1, 2] = 1
        cm[2, 0] = 1
        
        encoder = MotifEncoder(cm)
        results = encoder.run()
        
        self.assertIn('FeedbackLoop', results['instances'])
        self.assertEqual(len(results['instances']['FeedbackLoop']), 1)

if __name__ == '__main__':
    unittest.main()
