import numpy as np
import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from integration.Universal_D_v2_Encoder import UniversalDv2Encoder
from dynamics.Boolean_Dynamics import BooleanDynamics
from complexity.Trajectory_LZ import TrajectoryLZ

class HybridEncoder(UniversalDv2Encoder):
    """
    Hybrid Encoder (Level 5 Protocol)
    Combines Structural Complexity (D_struct) and Dynamical Complexity (D_dyn).
    D_hybrid = alpha * D_struct + beta * D_dyn
    """
    
    def __init__(self, network_data, block_sizes=[3, 4, 5, 6]):
        """
        Initialize with network data (JSON).
        Extracts adjacency for structural analysis.
        Keeps full data for dynamical simulation.
        """
        self.network_data = network_data
        
        # Extract Adjacency Matrix
        self.adj = self._extract_adjacency(network_data)
        
        # Initialize Structural Encoder
        super().__init__(self.adj, block_sizes=block_sizes)
        
        # Cache
        self.d_struct = None
        self.d_dyn = None
        
    def _extract_adjacency(self, data):
        """Helper to get adjacency matrix from JSON data"""
        nodes = data.get('nodes', [])
        n = len(nodes)
        if n == 0:
            return np.zeros((0,0))
            
        if 'cm' in data:
            adj = np.array(data['cm'])
            if adj.shape == (n, n):
                return adj
                
        # Fallback to edges
        node_map = {name: i for i, name in enumerate(nodes)}
        adj = np.zeros((n, n), dtype=int)
        edges = data.get('edges', [])
        for edge in edges:
            src = edge.get('source')
            tgt = edge.get('target')
            if src in node_map and tgt in node_map:
                adj[node_map[src], node_map[tgt]] = 1
        return adj

    def compute_hybrid_complexity(self, alpha=0.5, beta=0.5, steps=1000, initial_state='random', trials=10):
        """
        Compute Hybrid Complexity.
        
        Args:
            alpha (float): Weight for structural complexity.
            beta (float): Weight for dynamical complexity.
            steps (int): Simulation steps.
            initial_state (str): 'random'
            trials (int): Number of random initial conditions to average D_dyn over.
            
        Returns:
            dict: {
                'd_struct': float,
                'd_dyn': float,
                'd_hybrid': float,
                'details': dict
            }
        """
        # 1. Compute Structural Complexity (if not cached)
        if self.d_struct is None:
            struct_res = self.compute() # method from UniversalDv2Encoder
            # UniversalDv2Encoder returns a dict, not a float directly
            # The 'dv2' key holds the value.
            # Normalization? D_v2 scales with size. LZ is normalized.
            # We should normalize D_v2 by N^2 or similar to make them comparable?
            # Or just use raw bits. The hypothesis says D_bio << D_rand.
            # Let's use raw D_v2 for now as per previous protocol.
            self.d_struct = struct_res.get('dv2', 0.0)
            
        # 2. Compute Dynamical Complexity (if not cached)
        if self.d_dyn is None:
            sim = BooleanDynamics(self.network_data)
            lz_values = []
            
            for _ in range(trials):
                traj = sim.simulate(steps=steps, initial_state=initial_state)
                # Use flattened LZ
                lz = TrajectoryLZ.compute_trajectory_lz(traj, method='flatten')
                lz_values.append(lz)
                
            self.d_dyn = np.mean(lz_values)
            
        # 3. Combine
        # Note: D_struct is in bits (Description Length).
        # D_dyn (LZ) is normalized complexity (0 to 1 approx, or bits/char).
        # If D_struct is ~1000 and D_dyn is ~0.1, alpha/beta need to account for scale.
        # Or we normalize D_struct by N^2.
        # For this implementation, we assume alpha/beta handles scaling.
        
        d_hybrid = alpha * self.d_struct + beta * self.d_dyn
        
        return {
            'd_struct': self.d_struct,
            'd_dyn': self.d_dyn,
            'd_hybrid': d_hybrid,
            'alpha': alpha,
            'beta': beta
        }
