
import unittest
import numpy as np
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from stats.Bayes_Factor_Calculator import BayesFactorCalculator

class TestBayesFactorCalculator(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)
        self.null_mean = 100.0
        self.null_std = 10.0

    def test_strong_evidence_for_H1(self):
        """Test that distinct data yields high BF10"""
        # Data centered at 130 (3 sigma away)
        data = np.random.normal(130, 10, 50)
        result = BayesFactorCalculator.calculate_bayes_factor(data, self.null_mean, self.null_std)
        
        self.assertGreater(result['BF10'], 100, "BF10 should be > 100 for 3-sigma deviation")
        self.assertEqual(result['interpretation'], "Very Strong")

    def test_evidence_for_H0(self):
        """Test that matching data yields BF10 < 1 (Evidence for H0)"""
        # Data centered at 100 (matches null)
        data = np.random.normal(100, 10, 50)
        result = BayesFactorCalculator.calculate_bayes_factor(data, self.null_mean, self.null_std)
        
        # H0 (0 params) should be favored over H1 (2 params) due to BIC penalty
        self.assertLess(result['BF10'], 1.0, "BF10 should be < 1 when data matches null model")
        self.assertGreater(result['BF01'], 1.0, "BF01 should be > 1 when data matches null model")
        
    def test_insufficient_data(self):
        """Test error handling for small N"""
        with self.assertRaises(ValueError):
            BayesFactorCalculator.calculate_bayes_factor([100], 100, 10)

if __name__ == '__main__':
    unittest.main()
