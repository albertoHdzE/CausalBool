import numpy as np
import math

class TrajectoryLZ:
    """
    Computes Lempel-Ziv Complexity (LZ76) for dynamical trajectories.
    Implementation based on Kaspar and Schuster (1987).
    """
    
    @staticmethod
    def compute_lz76(s):
        """
        Calculate LZ76 complexity of a binary string s.
        
        Ref: Kaspar, F., & Schuster, H. G. (1987). 
        Easily calculable measure for the complexity of spatiotemporal patterns. 
        Physical Review A, 36(2), 842.
        """
        if not s:
            return 0
            
        n = len(s)
        i = 0
        c = 1
        k = 1
        k_max = 1
        
        while True:
            if i + k > n:
                break
            
            sub = s[i : i+k]
            # Search space: history S[0 : i+k-1]
            # This means we look for sub in the string that ends just before the last char of sub
            search_space = s[0 : i+k-1]
            
            if sub in search_space:
                k += 1
            else:
                c += 1
                i += k
                k = 1
                
        return c

    @staticmethod
    def compute_trajectory_lz(trajectory_matrix, method='flatten'):
        """
        Compute LZ complexity of a trajectory matrix (Time x Nodes).
        
        Args:
            trajectory_matrix (np.ndarray): Shape (T, N)
            method (str): 
                'flatten': Concatenate rows into one long string.
                'sum': Sum of LZ of each node's column.
                
        Returns:
            float: The LZ complexity.
        """
        T, N = trajectory_matrix.shape
        
        if method == 'flatten':
            # Flatten row-major (time-step by time-step)
            # This preserves the state vector structure in the sequence
            flat = trajectory_matrix.flatten()
            # Convert to binary string
            binary_string = "".join(flat.astype(str))
            lz = TrajectoryLZ.compute_lz76(binary_string)
            
            # Normalize? 
            # C_norm = C * log2(n) / n
            n = len(binary_string)
            if n > 1:
                norm = n / np.log2(n)
                return lz / norm
            return lz
            
        elif method == 'sum':
            total_lz = 0
            for j in range(N):
                col = trajectory_matrix[:, j]
                binary_string = "".join(col.astype(str))
                lz = TrajectoryLZ.compute_lz76(binary_string)
                
                # Normalize per column
                n = len(binary_string)
                if n > 1:
                    norm = n / np.log2(n)
                    total_lz += (lz / norm)
                else:
                    total_lz += lz
                    
            return total_lz / N # Average normalized LZ per node
            
        else:
            raise ValueError(f"Unknown method: {method}")
