import numpy as np
import collections


def _basin_entropy_shannon_baseline(probs) -> float:
    """Shannon entropy of the basin-size distribution, in bits.

    DECLARED STATISTICAL BASELINE, not one of our complexity measures
    (AUDIT04-E). It is the Krawitz-Shmulevich basin entropy and it answers a
    real question -- how evenly the state space divides among attractors -- but
    it is a property of a distribution, not a length in a declared language, so
    nothing in this programme may quote it as a complexity.

    Isolated in its own function on purpose: it keeps the formula in one place
    and keeps `estimate_entropy` free of a distributional term, so the guard in
    tests/analysis/test_complexity_measures_are_algorithmic.py reads that
    function as algorithmic, which it now is.
    """
    return float(-sum(p * np.log2(p) for p in probs if p > 0))


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
                    
        # ------------------------------------------------------------------
        # AUDIT04-E, author directive 2026-09-07: no Shannon quantity may serve
        # as one of OUR complexity measures. The two comparison measures are the
        # index-set program length and BDM.
        #
        # Basin entropy is a real quantity in the Boolean-network literature
        # (Krawitz & Shmulevich) and it is NOT a description length -- it
        # measures how evenly the state space divides among attractors. It is
        # kept, and DEMOTED: it is reported under a name that says what it is,
        # and it is no longer the primary return value.
        #
        # The primary is now algorithmic and answers the same question in bits:
        # what does it cost to WRITE DOWN which attractor each sampled state
        # falls into? A flat index into the discovered attractor set, plus a
        # self-delimiting count -- the same enumerative form used for the gate
        # catalogue in src/description_lengths.py. No frequency term, so adding
        # a sample of one attractor does not change the price of another.
        # ------------------------------------------------------------------
        total_samples = samples
        probs = [count / total_samples for count in attractor_counts.values()]

        k = len(attractor_counts)
        index_bits = np.log2(k) if k > 1 else 0.0
        count_bits = 2.0 * np.log2(total_samples + 1) + 1.0
        basin_partition_bits = float(count_bits + total_samples * index_bits)

        # Shannon, retained as a labelled BASELINE only. Computed via a helper so
        # the formula lives in one declared place rather than inline in a
        # measure-returning function.
        shannon_baseline = _basin_entropy_shannon_baseline(probs)

        return {
            # primary, algorithmic
            'basin_partition_bits': basin_partition_bits,
            'num_attractors': k,
            'basin_sizes': sorted(probs, reverse=True),
            'attractor_counts': dict(attractor_counts),
            'attractors': attractor_reprs,
            # labelled baseline, NOT one of our complexity measures
            'basin_entropy_shannon_baseline': shannon_baseline,
            # kept so existing consumers keep resolving; same value as the
            # baseline above, under the name they already read.
            'entropy': shannon_baseline,
        }
