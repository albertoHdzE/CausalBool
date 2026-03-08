
import os
import sys
import json
import re
import glob
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from datetime import datetime

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from integration.Universal_D_v2_Encoder import UniversalDv2Encoder

class BioNetworkOverlay:
    def __init__(self):
        self.results = []
        self.processed_dir = os.path.join(os.path.dirname(__file__), '../../data/bio/processed')
        self.sweep_path = os.path.join(os.path.dirname(__file__), '../../results/bio/phase_transition/phase_transition_sweep.csv')
        self.output_csv = os.path.join(os.path.dirname(__file__), '../../results/bio/phase_transition/bio_overlay.csv')
        self.output_plot = os.path.join(os.path.dirname(__file__), '../../doc/finalpaper/figures/phase_transition_overlay.png')

    def load_network(self, filepath):
        with open(filepath, 'r') as f:
            return json.load(f)

    def parse_logic(self, logic_str, node_names):
        """
        Parses a logic string like "AND(A, NOT(B))" into a python callable.
        Uses a simple substitution to Python syntax.
        """
        if logic_str == "INPUT":
            return lambda state: state # Identity (will be handled by index mapping usually)
            
        # Replace operators
        # Note: Order matters.
        # AND(a, b) -> (a and b) ? No, these are usually boolean 0/1 integers in simulation
        # Let's use bitwise or arithmetic: AND -> min/prod, OR -> max, NOT -> 1-x
        
        # Simple recursive parser or regex substitution is hard for nested calls.
        # But Cell Collective strings are usually uniform.
        
        # Strategy: Replace with Python bitwise operators for 0/1 integers
        # AND(x, y) -> (x & y)
        # OR(x, y) -> (x | y)
        # NOT(x) -> (1 - x)
        
        # BUT "AND(A, B, C)" can have multiple args.
        # Python's all() / any() are good but syntax conversion is tricky.
        
        # Hacky Eval Approach:
        # Define functions AND, OR, NOT in the local scope of eval
        
        def AND(*args):
            return 1 if all(args) else 0
        
        def OR(*args):
            return 1 if any(args) else 0
        
        def NOT(arg):
            return 1 - arg
            
        # Create a safe context
        context = {'AND': AND, 'OR': OR, 'NOT': NOT}
        
        # Add variables to context (will be passed at runtime)
        # We need to return a function that takes 'state' (list/array)
        # and maps node names to state indices.
        
        node_map = {name: i for i, name in enumerate(node_names)}
        
        # Replace node names in logic_str with state lookups?
        # logic_str contains names. 
        # e.g. "AND(CII, NOT(Cro))"
        # We need to be careful not to replace substrings of other names.
        # Regex word boundaries \bNAME\b
        
        # We will dynamically compile this.
        
        def logic_func(state):
            # Update context with current state values
            local_ctx = context.copy()
            for name, idx in node_map.items():
                local_ctx[name] = state[idx]
            
            try:
                # Handle "INPUT" special case if it slipped through
                if logic_str == "INPUT":
                    return state[node_map.get(logic_str, 0)] # Fallback
                    
                return eval(logic_str, {"__builtins__": {}}, local_ctx)
            except Exception as e:
                # print(f"Error evaluating logic '{logic_str}': {e}")
                return 0
                
        return logic_func

    def simulate(self, logic_funcs, n_nodes, steps=100):
        # Random initial state
        state = np.random.randint(0, 2, n_nodes)
        history = [state.copy()]
        
        for _ in range(steps):
            new_state = np.zeros(n_nodes, dtype=int)
            for i in range(n_nodes):
                if logic_funcs[i] is None: # Input or fixed
                    new_state[i] = state[i]
                else:
                    new_state[i] = logic_funcs[i](state)
            state = new_state
            history.append(state.copy())
            
        return np.array(history).T # Nodes x Time

    def compute_d_v2(self, matrix):
        if matrix.size == 0: return 0
        encoder = UniversalDv2Encoder(matrix)
        return encoder.compute()["dv2"]

    def analyze_network(self, net_data):
        name = net_data.get('name', 'unknown')
        nodes = net_data.get('nodes', [])
        logic = net_data.get('logic', {})
        cm = np.array(net_data.get('cm', []))
        
        if not nodes or cm.size == 0:
            print(f"Skipping {name}: No nodes or CM.")
            return None
            
        n_nodes = len(nodes)
        
        # 1. Parse Logic
        logic_funcs = []
        xor_count = 0
        
        for i, node in enumerate(nodes):
            rule = logic.get(node, "INPUT")
            
            # Check for XOR-ness in string
            if "XOR" in rule or "PARITY" in rule:
                xor_count += 1
                
            if rule == "INPUT":
                logic_funcs.append(None) # Identity
            else:
                logic_funcs.append(self.parse_logic(rule, nodes))
        
        p_xor = xor_count / n_nodes if n_nodes > 0 else 0
        
        # 2. Structural Complexity (D_struct)
        d_struct = self.compute_d_v2(cm)
        
        # 3. Behavioral Complexity (K_behav)
        space_time = self.simulate(logic_funcs, n_nodes, steps=100)
        k_behav = self.compute_d_v2(space_time)
        
        # 4. AER
        aer = k_behav / max(1.0, d_struct)
        
        return {
            "network": name,
            "p_xor": p_xor,
            "aer": aer,
            "d_struct": d_struct,
            "k_behav": k_behav
        }

    def run(self):
        print(f"[{datetime.now()}] Starting Bio Network Overlay Analysis...")
        
        # Load Bio Networks list from simplicity_v2_real.json to know which ones to process
        simplicity_path = os.path.join(os.path.dirname(__file__), '../../results/bio/simplicity_v2_real.json')
        with open(simplicity_path, 'r') as f:
            target_networks = [item['network'] for item in json.load(f)]
            
        results = []
        
        for net_name in target_networks:
            file_path = os.path.join(self.processed_dir, f"{net_name}.json")
            if not os.path.exists(file_path):
                print(f"Warning: File not found for {net_name}")
                continue
                
            print(f"Processing {net_name}...")
            net_data = self.load_network(file_path)
            res = self.analyze_network(net_data)
            if res:
                results.append(res)
                
        df = pd.DataFrame(results)
        os.makedirs(os.path.dirname(self.output_csv), exist_ok=True)
        df.to_csv(self.output_csv, index=False)
        print(f"Saved bio results to {self.output_csv}")
        
        self.plot_overlay(df)
        
    def plot_overlay(self, bio_df):
        # Load sweep data
        if not os.path.exists(self.sweep_path):
            print("Sweep data not found. Cannot plot overlay.")
            return
            
        sweep_df = pd.read_csv(self.sweep_path)
        
        plt.figure(figsize=(10, 6))
        
        # Plot Sweep Curve
        plt.plot(sweep_df['p_xor'], sweep_df['mean_aer'], 'b-', label='Synthetic Sweep (Mean AER)')
        plt.fill_between(sweep_df['p_xor'], 
                         sweep_df['mean_aer'] - sweep_df['std_aer'],
                         sweep_df['mean_aer'] + sweep_df['std_aer'], 
                         color='b', alpha=0.2, label='Standard Deviation')
                         
        # Plot Bio Networks
        # Since most bio p_xor ~ 0, we might want to jitter them or just plot them
        # If they are all at 0, they will stack.
        
        # Check if we have variation in p_xor
        unique_p = bio_df['p_xor'].unique()
        print(f"Bio p_XOR values: {unique_p}")
        
        plt.scatter(bio_df['p_xor'], bio_df['aer'], c='r', s=100, marker='*', label='Biological Networks', zorder=5)
        
        # Annotate top networks
        for _, row in bio_df.iterrows():
            plt.annotate(row['network'], (row['p_xor'], row['aer']), 
                         xytext=(5, 5), textcoords='offset points', fontsize=8)
        
        plt.title('Phase Transition: Algorithmic Efficiency Ratio (AER)\nSynthetic Sweep vs Biological Networks')
        plt.xlabel('p_XOR (Fraction of Parity Functions)')
        plt.ylabel('AER (Behavioral Complexity / Structural Complexity)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        os.makedirs(os.path.dirname(self.output_plot), exist_ok=True)
        plt.savefig(self.output_plot, dpi=300)
        print(f"Saved plot to {self.output_plot}")

if __name__ == "__main__":
    overlay = BioNetworkOverlay()
    overlay.run()
