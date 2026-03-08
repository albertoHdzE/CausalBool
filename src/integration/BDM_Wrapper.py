
import numpy as np
from pybdm import BDM
from typing import Tuple, Dict, Any

class BDMWrapper:
    """
    Wrapper class for the Block Decomposition Method (BDM) library.
    Used to estimate algorithmic complexity of binary matrices.
    """
    
    def __init__(self, ndim: int = 2):
        """
        Initialize BDM instance.
        
        Args:
            ndim (int): Number of dimensions (default 2 for matrices).
        """
        self.bdm = BDM(ndim=ndim)
        
    def compute_bdm(self, matrix: np.ndarray) -> Dict[str, Any]:
        """
        Compute the BDM value for a given binary matrix.
        
        Args:
            matrix (np.ndarray): Binary matrix (numpy array).
            
        Returns:
            Dict containing:
                - 'bdm_value': The calculated BDM complexity.
                - 'entropy': Shannon entropy (for comparison).
                - 'shape': Shape of the input matrix.
        """
        if not isinstance(matrix, np.ndarray):
            matrix = np.array(matrix)
            
        # Ensure matrix is integer type (0/1)
        matrix = matrix.astype(int)
        
        bdm_value = self.bdm.bdm(matrix)
        entropy_value = self.bdm.ent(matrix)
        
        return {
            "bdm_value": float(bdm_value),
            "entropy": float(entropy_value),
            "shape": matrix.shape
        }

    @staticmethod
    def compare_complexity(matrix_a: np.ndarray, matrix_b: np.ndarray) -> Dict[str, float]:
        """
        Compare BDM complexity of two matrices.
        Returns the difference (A - B).
        """
        wrapper = BDMWrapper()
        bdm_a = wrapper.compute_bdm(matrix_a)["bdm_value"]
        bdm_b = wrapper.compute_bdm(matrix_b)["bdm_value"]
        
        return {
            "bdm_a": bdm_a,
            "bdm_b": bdm_b,
            "diff": bdm_a - bdm_b,
            "ratio": bdm_a / bdm_b if bdm_b != 0 else float('inf')
        }
