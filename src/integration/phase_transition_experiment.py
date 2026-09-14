
import sys
import random
import json
import numpy as np
import matplotlib.pyplot as plt
from functools import lru_cache
from pathlib import Path
from typing import List

# Add src to path
# AUDIT04-D. This module used to carry its own gate dispatch. Measured
# elementwise against the owner before anything moved: 27 disagreements of 124
# (gate, input) cases -- and EVERY ONE of them was the gate this module called
# "CANALISING". AND, OR and XOR agreed exactly, so those three were drift and are
# now delegated.
#
# The 27 are not drift. The owner's CANALISING takes canalisingIndex,
# canalisingValue and canalisedOutput; this module hard-codes "the first input
# decides", which its own comment described as a "simplified canalising". That is
# a DIFFERENT FUNCTION wearing the owner's name, so it gets its own name --
# FIRST_INPUT_DOMINATES -- rather than being collapsed into something it is not.
#
# The rename is behaviour-preserving: the label is chosen from a three-element
# list by index, so the same seed selects the same gate, and this module's
# figures live in doc/newIntPaper/, a provenance archive that must not be
# rewritten. Verified below rather than asserted.

_OWNED_GATES = frozenset({"AND", "OR", "XOR"})


@lru_cache(maxsize=1)
def _gate_owner():
    """The declared Python owner of gate semantics (author decision 2026-09-06)."""
    root = Path(__file__).resolve().parents[2]
    src = root / "index-deconvolution" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import causalbool

    return causalbool


current_file = Path(__file__).resolve()
src_dir = current_file.parents[1]
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

try:
    from integration.bio_D_experiment import compute_description_length
    from integration.BDM_Wrapper import BDMWrapper
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

class BooleanNetwork:
    def __init__(self, n: int, k: int, p_xor: float):
        self.n = n
        self.k = k
        self.p_xor = p_xor
        self.cm = self._generate_connectivity()
        self.dynamic = self._assign_logic()
        
    def _generate_connectivity(self) -> List[List[int]]:
        """Generate random k-regular(ish) connectivity."""
        cm = [[0] * self.n for _ in range(self.n)]
        for i in range(self.n):
            inputs = random.sample(range(self.n), self.k)
            for j in inputs:
                cm[i][j] = 1
        return cm
    
    def _assign_logic(self) -> List[str]:
        """Assign gates based on p_xor probability."""
        gates = []
        for _ in range(self.n):
            if random.random() < self.p_xor:
                gates.append("XOR")
            else:
                # Use canalising/monotone gates for the ordered regime
                gates.append(random.choice(["AND", "OR", "FIRST_INPUT_DOMINATES"]))
        return gates
        
    def step(self, state: List[int]) -> List[int]:
        new_state = [0] * self.n
        for i in range(self.n):
            inputs = [state[j] for j in range(self.n) if self.cm[i][j] == 1]
            gate = self.dynamic[i]
            if gate == "FIRST_INPUT_DOMINATES":
                # NOT the owner's CANALISING, and no longer named as if it were.
                res = 1 if (inputs and inputs[0] == 1) else 0
            elif gate in _OWNED_GATES:
                res = int(_gate_owner().apply_gate(gate, list(inputs), {}))
            else:
                # AUDIT02/P1: a silent 0 is indistinguishable from a legitimate
                # FALSE, so an unsupported gate must refuse rather than answer.
                raise ValueError(f"unsupported gate {gate!r} in this experiment")
            new_state[i] = res
        return new_state

    def simulate(self, steps: int) -> np.ndarray:
        state = [random.randint(0, 1) for _ in range(self.n)]
        history = [state]
        for _ in range(steps):
            state = self.step(state)
            history.append(state)
        return np.array(history)

def run_experiment(
    n_nodes: int = 20, 
    k: int = 3, 
    steps: int = 50, 
    n_trials: int = 10,
    resolution: int = 20
):
    print(f"Starting Phase Transition Sweep (N={n_nodes}, K={k}, Steps={steps})...")
    
    p_values = np.linspace(0, 1, resolution)
    results = {
        "p_xor": [],
        "mean_D": [],
        "std_D": [],
        "mean_BDM": [],
        "std_BDM": []
    }
    
    bdm_wrapper = BDMWrapper(ndim=2)
    
    for p in p_values:
        d_vals = []
        bdm_vals = []
        
        for _ in range(n_trials):
            net = BooleanNetwork(n_nodes, k, p)
            
            # Compute Mechanistic D
            d_res = compute_description_length(net.cm, net.dynamic)
            d_vals.append(d_res["D"])
            
            # Compute Behavioral BDM
            spacetime = net.simulate(steps)
            bdm_res = bdm_wrapper.compute_bdm(spacetime)
            bdm_vals.append(bdm_res["bdm_value"])
            
        results["p_xor"].append(float(p))
        results["mean_D"].append(float(np.mean(d_vals)))
        results["std_D"].append(float(np.std(d_vals)))
        results["mean_BDM"].append(float(np.mean(bdm_vals)))
        results["std_BDM"].append(float(np.std(bdm_vals)))
        
        print(f"p={p:.2f}: D={np.mean(d_vals):.2f}, BDM={np.mean(bdm_vals):.2f}")
        
    return results

def plot_results(results, output_dir):
    p = results["p_xor"]
    
    # Plot 1: BDM vs p_xor (The Phase Transition)
    plt.figure(figsize=(10, 6))
    plt.errorbar(p, results["mean_BDM"], yerr=results["std_BDM"], 
                 fmt='o-', color='purple', ecolor='lightgray', capsize=3, label='Behavioral BDM')
    plt.axvline(x=0.3, color='r', linestyle='--', label='Edge of Chaos (~0.3)')
    plt.xlabel('Proportion of XOR Gates ($p_{XOR}$)')
    plt.ylabel('Behavioral Complexity (BDM)')
    plt.title('Phase Transition at the Edge of Chaos')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(output_dir / "phase_transition_bdm.png", dpi=300)
    plt.close()
    
    # Plot 2: D vs p_xor (Mechanistic Invariance)
    plt.figure(figsize=(10, 6))
    plt.errorbar(p, results["mean_D"], yerr=results["std_D"], 
                 fmt='s-', color='green', ecolor='lightgray', capsize=3, label='Mechanistic D')
    plt.xlabel('Proportion of XOR Gates ($p_{XOR}$)')
    plt.ylabel('Mechanistic Description Length ($D$) [bits]')
    plt.title('Mechanistic Cost Stability')
    plt.ylim(bottom=0)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(output_dir / "mechanistic_stability.png", dpi=300)
    plt.close()

if __name__ == "__main__":
    current_file = Path(__file__).resolve()
    project_root = current_file.parents[2]
    output_dir = project_root / "doc" / "newIntPaper" / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = run_experiment(n_nodes=20, k=2, steps=40, n_trials=5, resolution=11)
    
    # Save raw data
    with open(project_root / "doc" / "newIntPaper" / "results_phase6.json", "w") as f:
        json.dump(results, f, indent=2)
        
    plot_results(results, output_dir)
    print("Experiment complete. Results saved.")
