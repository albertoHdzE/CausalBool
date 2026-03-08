import os
import sys
import json
import numpy as np
import pandas as pd
import networkx as nx
import random
from datetime import datetime

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from integration.Universal_D_v2_Encoder import UniversalDv2Encoder

class PhaseTransitionAnalyzer:
    def __init__(self):
        self.results = []
        
    def generate_topology(self, n_nodes, density=2.0):
        # Generate Random Graph (Erdos-Renyi)
        p = density / n_nodes
        G = nx.erdos_renyi_graph(n_nodes, p, directed=True)
        # Ensure connectivity? Not strictly necessary for this exp
        return nx.to_numpy_array(G, dtype=int)
        
    def assign_logic(self, adj, p_xor):
        n_nodes = adj.shape[0]
        logic_funcs = []
        
        for i in range(n_nodes):
            inputs = np.where(adj[:, i] == 1)[0]
            k = len(inputs)
            
            if k == 0:
                # Fixed node (random state)
                state = random.randint(0, 1)
                logic_funcs.append(lambda x, s=state: s)
                continue
                
            # Choose function type
            if random.random() < p_xor:
                # XOR (Parity)
                # Returns 1 if odd number of inputs are 1
                func = lambda x, idx=inputs: int(sum(x[j] for j in idx) % 2)
            else:
                # Canalizing (Mix of AND/OR)
                # To avoid bias to 0 or 1, split 50/50 between AND/OR-like
                if random.random() < 0.5:
                    # OR-like: 1 if any input is 1
                    func = lambda x, idx=inputs: 1 if any(x[j] for j in idx) else 0
                else:
                    # AND-like: 1 if all inputs are 1
                    func = lambda x, idx=inputs: 1 if all(x[j] for j in idx) else 0
            
            logic_funcs.append(func)
            
        return logic_funcs

    def simulate(self, logic_funcs, steps=50):
        n_nodes = len(logic_funcs)
        # Random initial state
        state = [random.randint(0, 1) for _ in range(n_nodes)]
        history = [state]
        
        for _ in range(steps):
            new_state = []
            for i, func in enumerate(logic_funcs):
                new_state.append(func(state))
            state = new_state
            history.append(state)
            
        return np.array(history).T # Nodes x Time
        
    def compute_d_v2(self, matrix):
        if matrix.size == 0:
            return 0
        encoder = UniversalDv2Encoder(matrix)
        result = encoder.compute()
        return result["dv2"]

    def run_sweep(self, n_nodes=20, steps=50, n_points=11, n_reps=5):
        print(f"[{datetime.now()}] Starting Phase Transition Sweep...")
        print(f"  Nodes: {n_nodes}, Steps: {steps}, Points: {n_points}, Reps: {n_reps}")
        
        results = []
        
        # p_xor from 0.0 to 1.0
        p_values = np.linspace(0, 1, n_points)
        
        for p in p_values:
            print(f"  Testing p_XOR = {p:.2f} ...")
            metrics = {'aer': [], 'd_struct': [], 'k_behav': []}
            
            for _ in range(n_reps):
                # 1. Generate Network
                adj = self.generate_topology(n_nodes)
                logic = self.assign_logic(adj, p)
                
                # 2. Structural Complexity
                d_struct = self.compute_d_v2(adj)
                
                # 3. Behavioral Complexity
                space_time = self.simulate(logic, steps=steps)
                k_behav = self.compute_d_v2(space_time)
                
                # 4. AER
                # Avoid div by zero
                aer = k_behav / max(1.0, d_struct)
                
                metrics['aer'].append(aer)
                metrics['d_struct'].append(d_struct)
                metrics['k_behav'].append(k_behav)
                
            results.append({
                "p_xor": p,
                "mean_aer": np.mean(metrics['aer']),
                "std_aer": np.std(metrics['aer']),
                "mean_d_struct": np.mean(metrics['d_struct']),
                "mean_k_behav": np.mean(metrics['k_behav'])
            })
            
        self.results = results
        return pd.DataFrame(results)

if __name__ == "__main__":
    analyzer = PhaseTransitionAnalyzer()
    df = analyzer.run_sweep(n_nodes=20, steps=100, n_points=11, n_reps=10)
    
    out_path = "results/bio/phase_transition/phase_transition_sweep.csv"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_csv(out_path, index=False)
    
    print("Sweep Complete. Results saved.")
    print(df)
