
import unittest
import numpy as np
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from complexity.Scaling_LZ_Tools import ComplexityScaler
from integration.Universal_D_v2_Encoder import UniversalDv2Encoder

class TestComplexityScaler(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)

    def test_lz_complexity(self):
        """Test Lempel-Ziv Complexity on simple and random strings"""
        # Simple string: "000000..."
        s_simple = "0" * 100
        lz_simple = ComplexityScaler.compute_lz_complexity(s_simple)
        
        # Periodic string: "010101..."
        s_periodic = "01" * 50
        lz_periodic = ComplexityScaler.compute_lz_complexity(s_periodic)
        
        # Random string
        s_random = "".join([str(x) for x in np.random.randint(0, 2, 100)])
        lz_random = ComplexityScaler.compute_lz_complexity(s_random)
        
        # Expect: Simple < Periodic < Random
        self.assertLess(lz_simple, lz_periodic)
        self.assertLess(lz_periodic, lz_random)
        
        print(f"LZ(Simple): {lz_simple}, LZ(Periodic): {lz_periodic}, LZ(Random): {lz_random}")

    def test_scaling_exponent_differentiation(self):
        """Test that Scaling Exponent differs between Random and Structured"""
        # Random Matrix 32x32
        m_rand = np.random.randint(0, 2, (32, 32))
        
        # Structured Matrix (Checkerboard)
        m_struct = np.zeros((32, 32), dtype=int)
        m_struct[::2, ::2] = 1
        m_struct[1::2, 1::2] = 1
        
        # Compute Scaling
        # We expect D to behave differently.
        # Note: UniversalDv2Encoder must be available.
        
        res_rand = ComplexityScaler.compute_scaling_exponent(m_rand, block_sizes=[4, 5, 6])
        res_struct = ComplexityScaler.compute_scaling_exponent(m_struct, block_sizes=[4, 5, 6])
        
        print(f"Alpha(Rand): {res_rand['alpha']:.4f}, Alpha(Struct): {res_struct['alpha']:.4f}")
        
        # Validation: Just check they are calculated and result is valid float
        self.assertIsNotNone(res_rand['alpha'])
        self.assertIsNotNone(res_struct['alpha'])
        
        # We assume they should be different.
        # Typically Random has higher D.
        # Scaling behavior might also differ.
        self.assertNotAlmostEqual(res_rand['alpha'], res_struct['alpha'], delta=0.1)

if __name__ == '__main__':
    unittest.main()
