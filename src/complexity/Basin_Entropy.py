import numpy as np
import collections

class BasinEntropyEstimator:
    """
    Estimates Basin Entropy using Monte Carlo sampling of initial states.
    Uses BooleanDynamics with Asynchronous updates.
    """
    
    def __init__(self, dynamics_simulator):
        self.sim = dynamics_simulator
        
    def estimate_entropy(self, samples=1000, max_steps=2000, window_size=50):
        """
        Estimate Basin Entropy.
        
        Args:
            samples: Number of random initial states to sample.
            max_steps: Maximum steps to simulate per sample.
            window_size: Window size to detect attractors (simple cycle detection).
            
        Returns:
            dict: {
                'entropy': float (bits),
                'num_attractors': int,
                'attractor_sizes': dict (attractor_hash -> count),
                'attractors': dict (attractor_hash -> representative_state_str)
            }
        """
        attractor_counts = collections.defaultdict(int)
        attractor_reprs = {}
        
        # Run batch simulation for efficiency
        # However, attractors might be reached at different times.
        # Simple approach: Run simulation for fixed steps, then check last window.
        # Better: Run batch, check convergence.
        
        # Let's run in batches of 100 for memory efficiency
        batch_size = 100
        num_batches = (samples + batch_size - 1) // batch_size
        
        for b in range(num_batches):
            current_batch_size = min(batch_size, samples - b * batch_size)
            
            # Simulate
            # Note: For Async, "Attractor" is a loose term. 
            # We look for "Stationary Distribution" or "Trapping Sets".
            # In finite Boolean networks, it will eventually hit a set of states (Attractor) 
            # from which it cannot escape.
            # Detecting Async attractors is HARD. 
            # Simplification for Level 6:
            # Run for a long time (max_steps).
            # Take the *last* state as a proxy for the attractor basin.
            # Or take the last 'window_size' states, sort them, and hash the tuple to represent the "Attractor Set".
            
            trajectory = self.sim.simulate(
                steps=max_steps, 
                initial_state='random', 
                update_mode='asynchronous', 
                batch_size=current_batch_size
            )
            
            # Trajectory shape: (Steps+1, Batch, N)
            # Analyze last window for each sample
            last_window = trajectory[-window_size:, :, :] # (Window, Batch, N)
            
            for i in range(current_batch_size):
                # Get the sequence of states in the window for sample i
                sample_window = last_window[:, i, :] # (Window, N)
                
                # Identify the "Attractor"
                # For fixed points: all states in window are same.
                # For cycles: states repeat.
                # For complex async attractors: set of states.
                # We define the attractor ID by the set of unique states visited in the window.
                # Sort them to ensure canonical representation.
                
                # Convert to bytes for hashing
                unique_states = np.unique(sample_window, axis=0)
                # Sort rows
                # Lexicographical sort of rows
                # unique_states is already sorted by np.unique
                
                # Hashable representation
                attractor_id = unique_states.tobytes()
                
                attractor_counts[attractor_id] += 1
                if attractor_id not in attractor_reprs:
                    attractor_reprs[attractor_id] = unique_states
                    
        # Compute Entropy
        total_samples = samples
        entropy = 0.0
        
        probs = []
        for count in attractor_counts.values():
            p = count / total_samples
            probs.append(p)
            if p > 0:
                entropy -= p * np.log2(p)
                
        return {
            'entropy': entropy,
            'num_attractors': len(attractor_counts),
            'basin_sizes': sorted(probs, reverse=True),
            'attractor_counts': dict(attractor_counts),
            'attractors': attractor_reprs
        }
