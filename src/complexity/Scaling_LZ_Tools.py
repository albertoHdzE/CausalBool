
import numpy as np
from scipy import stats
import math
import sys
import os

# Ensure src is in path to import integration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from integration.Universal_D_v2_Encoder import UniversalDv2Encoder
except ImportError:
    # Fallback or error if not found (will fail at runtime if needed)
    UniversalDv2Encoder = None

class ComplexityScaler:
    """
    Tools for Multi-Scale Complexity Analysis.
    1. Scaling Exponent: D(b) ~ b^alpha
    2. Lempel-Ziv Complexity (LZ76)
    """

    @staticmethod
    def compute_scaling_exponent(matrix, block_sizes=[3, 4, 5, 6]):
        """
        Computes the scaling exponent alpha of the Description Length D_v2 
        with respect to block size b.
        
        Args:
            matrix (np.array): Adjacency matrix.
            block_sizes (list): List of block sizes to test.
            
        Returns:
            dict: {
                'alpha': float,       # Scaling exponent
                'r_squared': float,   # Goodness of fit
                'details': dict       # D values for each b
            }
        """
        if UniversalDv2Encoder is None:
            raise ImportError("UniversalDv2Encoder not found in src/integration")

        d_values = []
        valid_sizes = []
        
        matrix = np.array(matrix)
        n = matrix.shape[0]

        for b in block_sizes:
            if b > n:
                continue
                
            # Use UniversalDv2Encoder with specific block size
            # The encoder usually takes a list, but we want D for *just* this b?
            # UniversalDv2Encoder sums over the provided block sizes.
            # So if we pass [b], it computes D for that b.
            encoder = UniversalDv2Encoder(matrix, block_sizes=[b])
            res = encoder.compute()
            d_val = res['dv2']
            
            # If D is 0 (e.g. empty matrix), log will fail.
            if d_val > 0:
                d_values.append(d_val)
                valid_sizes.append(b)
        
        if len(valid_sizes) < 2:
            return {'alpha': 0.0, 'r_squared': 0.0, 'details': {}}

        # Fit Power Law: D ~ b^alpha => ln(D) = alpha * ln(b) + C
        log_b = np.log(valid_sizes)
        log_d = np.log(d_values)
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(log_b, log_d)
        
        return {
            'alpha': slope,
            'r_squared': r_value**2,
            'details': dict(zip(valid_sizes, d_values))
        }

    @staticmethod
    def compute_lz_complexity(binary_string):
        """
        Computes Lempel-Ziv Complexity (LZ76) of a binary string.
        Implementation based on Kaspar and Schuster (1987).
        """
        s = binary_string
        n = len(s)
        if n == 0:
            return 0
            
        c = 1
        l = 1
        i = 0
        k = 1
        k_max = 1
        
        while True:
            if c + i + k > n: # Check bounds
                break
                
            # Look for s[i+k-1] in s[l+k-1]
            # Wait, standard Kaspar-Schuster algo:
            # Let S be the string.
            # c: complexity counter
            # i: index of current position
            # l: length of current substring
            pass
            # Let's use a simpler Pythonic set-based approach for LZ76 (dictionary size)
            # or exact Kaspar-Schuster.
            break # Re-implementing below
        
        # Simplified LZ76 (Vocabulary Size)
        # Parse s into phrases such that each phrase is the shortest substring 
        # not seen before.
        phrases = set()
        i = 0
        current_phrase = ""
        count = 0
        while i < n:
            current_phrase += s[i]
            if current_phrase not in phrases:
                phrases.add(current_phrase)
                count += 1
                current_phrase = ""
            i += 1
            
        # Normalization (optional, but raw LZ is count)
        return count

    @staticmethod
    def normalized_lz(binary_string):
        """Returns LZ complexity normalized by n/log2(n)"""
        n = len(binary_string)
        if n < 2: return 0
        lz = ComplexityScaler.compute_lz_complexity(binary_string)
        norm = n / np.log2(n)
        return lz / norm

if __name__ == "__main__":
    # Test Scaling
    # Mock Encoder for standalone test or use real if available
    pass
