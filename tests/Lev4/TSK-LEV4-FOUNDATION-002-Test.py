
import unittest
import numpy as np
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from stats.Mutual_Information_Analyzer import MutualInformationAnalyzer

class TestMutualInformationAnalyzer(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)

    def test_sine_wave_nonlinearity(self):
        """Test detection of non-linear dependency (Parabola)"""
        x = np.linspace(-1, 1, 200)
        # Parabola y = x^2 on symmetric interval has 0 correlation
        y = x**2 + np.random.normal(0, 0.05, 200)
        
        result = MutualInformationAnalyzer.compute_mutual_information(x, y)
        
        self.assertLess(abs(result['pearson_rho']), 0.3, "Pearson Rho should be low for parabola")
        self.assertGreater(result['MI_bits'], 0.5, "MI should be high (> 0.5 bits) for parabola")
        self.assertIn("Non-Linear", result['interpretation'])

    def test_linear_dependency(self):
        """Test linear dependency yields both high Rho and MI"""
        x = np.random.rand(100)
        y = 2*x + 1 + np.random.normal(0, 0.1, 100)
        
        result = MutualInformationAnalyzer.compute_mutual_information(x, y)
        
        self.assertGreater(abs(result['pearson_rho']), 0.9, "Pearson Rho should be high for linear")
        self.assertGreater(result['MI_bits'], 1.0, "MI should be high for linear")

    def test_random_noise(self):
        """Test independent random noise yields low MI"""
        x = np.random.rand(100)
        y = np.random.rand(100)
        
        result = MutualInformationAnalyzer.compute_mutual_information(x, y)
        
        self.assertLess(result['MI_bits'], 0.3, "MI should be low for random noise")
        self.assertIn("No Dependency", result['interpretation'])

if __name__ == '__main__':
    unittest.main()
