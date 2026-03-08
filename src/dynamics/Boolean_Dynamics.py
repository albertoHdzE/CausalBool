import numpy as np
import random
import json

class BooleanDynamics:
    """
    A high-performance simulator for synchronous and asynchronous Boolean updates.
    """
    
    def __init__(self, network_data):
        """
        Initialize with network data (JSON dict).
        Expects 'nodes' and 'logic' or 'edges'.
        """
        self.nodes = network_data.get('nodes', [])
        self.node_map = {name: i for i, name in enumerate(self.nodes)}
        self.n = len(self.nodes)
        
        # Parse Logic
        self.rules = self._parse_rules(network_data)
        
    def _parse_rules(self, data):
        """
        Parse logic rules. 
        Priority:
        1. Explicit 'logic' dictionary (node -> expression string) - TODO: Need parser
        2. Explicit 'truth_tables' (node -> list of ints)
        3. Infer from 'edges' (Activators AND NOT Inhibitors)
        """
        rules = []
        
        # Check for explicit logic (simplified for now, assuming missing or empty based on inspection)
        # If 'logic' exists and is not empty, we would need a parser. 
        # For this implementation, we focus on the fallback to edges which is common in the dataset.
        
        edges = data.get('edges', [])
        
        # Build adjacency lists
        activators = {i: [] for i in range(self.n)}
        inhibitors = {i: [] for i in range(self.n)}
        
        for edge in edges:
            src = edge.get('source')
            tgt = edge.get('target')
            etype = edge.get('type', 'activation')
            
            if src in self.node_map and tgt in self.node_map:
                s_idx = self.node_map[src]
                t_idx = self.node_map[tgt]
                
                if 'inhibition' in etype.lower():
                    inhibitors[t_idx].append(s_idx)
                else:
                    activators[t_idx].append(s_idx)
        
        # Compile rules into callable functions or efficient structures
        # Rule: (OR(activators) or (NO_ACTIVATORS -> 0)) AND NOT (OR(inhibitors))
        # Note: If no activators and no inhibitors, node usually stays constant or 0. 
        # Standard: Default 0. If only inhibitors, 0 (unless self-inhibition implies something else, but standard is 0).
        # Exception: If a node has NO inputs, it's an input node (stays constant).
        
        for i in range(self.n):
            acts = activators[i]
            inhibit = inhibitors[i]
            
            # Optimization: Store indices as numpy arrays
            rules.append({
                'acts': np.array(acts, dtype=int),
                'inhs': np.array(inhibit, dtype=int),
                'is_input': (len(acts) == 0 and len(inhibit) == 0)
            })
            
        return rules

    def step(self, state):
        """
        Perform one synchronous update step.
        state: boolean array of shape (N,) or (Batch, N)
        """
        new_state = state.copy()
        
        # If single state, expand dims for uniform handling
        if state.ndim == 1:
            batch_mode = False
            state = state[np.newaxis, :]
        else:
            batch_mode = True
            
        # Vectorized update? 
        # For general rules, hard to fully vectorize across nodes with different connectivity.
        # But we can vectorize across the batch.
        
        current_state = state # (Batch, N)
        next_state_batch = np.zeros_like(current_state)
        
        for i in range(self.n):
            rule = self.rules[i]
            
            if rule['is_input']:
                # Input nodes keep their state
                next_state_batch[:, i] = current_state[:, i]
                continue
                
            # Activation: Any activator is 1
            if len(rule['acts']) > 0:
                # current_state[:, rule['acts']] shape is (Batch, NumActs)
                # any(axis=1) -> (Batch,)
                act_condition = np.any(current_state[:, rule['acts']], axis=1)
            else:
                # No activators -> 0 (unless we define constitutive activation, but standard is 0)
                act_condition = np.zeros(current_state.shape[0], dtype=bool)
                
            # Inhibition: Any inhibitor is 1
            if len(rule['inhs']) > 0:
                inh_condition = np.any(current_state[:, rule['inhs']], axis=1)
            else:
                inh_condition = np.zeros(current_state.shape[0], dtype=bool)
            
            # Logic: Activators AND NOT Inhibitors
            # Exception handling: What if only inhibitors? Usually OFF.
            # What if no inputs? Handled by is_input.
            
            next_state_batch[:, i] = np.logical_and(act_condition, np.logical_not(inh_condition))
            
        if not batch_mode:
            return next_state_batch[0]
        return next_state_batch
        
    def step_async(self, state):
        """
        Perform one asynchronous update step.
        Selects one node at random to update for each sample in the batch.
        state: boolean array of shape (N,) or (Batch, N)
        """
        # If single state, expand dims for uniform handling
        if state.ndim == 1:
            state = state[np.newaxis, :]
            
        batch_size, n_nodes = state.shape
        next_state_batch = state.copy()
        
        # For each sample in batch, pick a random node to update
        # Vectorized implementation:
        # 1. Calculate all possible next states (synchronous step)
        # 2. Pick random indices
        # 3. Update only those indices
        
        # Calculate full next state (synchronous logic)
        full_next_state = self.step(state)
        
        # Generate random indices for each sample
        update_indices = np.random.randint(0, n_nodes, size=batch_size)
        
        # Apply updates
        # Create a mask or advanced indexing
        rows = np.arange(batch_size)
        next_state_batch[rows, update_indices] = full_next_state[rows, update_indices]
        
        return next_state_batch

    def simulate(self, steps=1000, initial_state='random', update_mode='synchronous', batch_size=1):
        """
        Simulate trajectory.
        initial_state: 'random' or numpy array (N,)
        update_mode: 'synchronous' or 'asynchronous'
        """
        if isinstance(initial_state, str) and initial_state == 'random':
            current_state = np.random.randint(0, 2, size=(batch_size, self.n))
        else:
            current_state = np.array(initial_state)
            if current_state.ndim == 1:
                current_state = current_state[np.newaxis, :]
                
        trajectory = [current_state.copy()]
        
        for _ in range(steps):
            if update_mode == 'synchronous':
                current_state = self.step(current_state)
            elif update_mode == 'asynchronous':
                current_state = self.step_async(current_state)
            trajectory.append(current_state.copy())
            
        # Return shape (Steps, Batch, N) -> Squeeze if batch=1
        trajectory = np.array(trajectory)
        if trajectory.shape[1] == 1:
            return trajectory[:, 0, :]
        return trajectory

def load_mammalian_cycle():
    # Helper for testing
    import os
    path = os.path.join(os.path.dirname(__file__), '../../data/bio/processed/ginsim_2006-mammal-cell-cycle_boolean_cell_cycle.json')
    with open(path, 'r') as f:
        return json.load(f)
