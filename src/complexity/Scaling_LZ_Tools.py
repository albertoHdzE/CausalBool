
import numpy as np
from scipy import stats
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
    def compute_lz78_dictionary_size(binary_string):
        """
        Number of phrases in the LZ78 parse of a binary string.

        The string is read left to right and cut whenever the phrase under
        construction has not been seen before; the return value is the size of
        the resulting phrase dictionary.

        THIS IS NOT LZ76, AND IT IS NOT KASPAR & SCHUSTER (1987), both of which
        this function's docstring previously claimed. AUDIT03-C measured the
        difference rather than assuming it:

          against the published Kaspar-Schuster LZ76   6 / 300 random strings
          against src/complexity/Trajectory_LZ.py     10 / 300 random strings

        The structured cases show why the two are not interchangeable. For
        "0" * 32, LZ76 returns 2 -- the phrases "0" and "000...0" -- whereas the
        LZ78 parse returns 7, because it must cut a new phrase every time the
        run lengthens. LZ78 dictionary size on a constant string grows like
        sqrt(n); LZ76 does not grow at all.

        Both are legitimate complexity measures. They are DIFFERENT measures,
        so under the monolithic-code law they get two names rather than one
        owner: 2 per cent elementwise agreement is not drift between copies, it
        is two concepts wearing one label.

        What was actually here before: an abandoned Kaspar-Schuster attempt.
        The loop it opened contained `pass` followed by
        `break  # Re-implementing below`, so it never executed a single
        iteration, and `l` and `k_max` were its leftovers -- not, as I first
        recorded them, markers of a deliberately simplified variant.
        """
        s = binary_string
        n = len(s)
        if n == 0:
            return 0

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
            
        return count

    @staticmethod
    def compute_lz_complexity(binary_string):
        """DEPRECATED forwarder to compute_lz78_dictionary_size.

        Kept rather than deleted, per the collapse protocol in
        GOVERNANCE/CORE.md section 6: a forwarder preserves the provenance of
        every result already produced under the old name. The name is retained
        only for compatibility -- it is misleading, because what it returns is
        an LZ78 dictionary size and not an LZ76 complexity.

        For LZ76 use src/complexity/Trajectory_LZ.py, which agrees with the
        published Kaspar-Schuster algorithm on 255 of 300 random strings.
        """
        return ComplexityScaler.compute_lz78_dictionary_size(binary_string)

    @staticmethod
    def normalized_lz(binary_string):
        """LZ78 dictionary size normalised by n/log2(n).

        The normalisation is the right one for this quantity -- an LZ78
        dictionary over a binary alphabet also grows as n/log2(n) for a random
        string -- so the divisor survives the relabelling above unchanged.
        """
        n = len(binary_string)
        if n < 2: return 0
        lz = ComplexityScaler.compute_lz78_dictionary_size(binary_string)
        norm = n / np.log2(n)
        return lz / norm

if __name__ == "__main__":
    # Test Scaling
    # Mock Encoder for standalone test or use real if available
    pass
