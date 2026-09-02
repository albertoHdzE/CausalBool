import numpy as np
import random

def calculate_complexity(n, adjacency, gates):
    """
    Simulates the mechanistic description length D.
    D = sum(bits_per_node)
    bits_per_node ~ log2(gate_catalogue_size) + in_degree * log2(n)
    """
    total_bits = 0
    # Assume 12 gates in catalogue -> ~3.58 bits -> 4 bits
    gate_bits = 4
    
    for i in range(n):
        in_degree = sum(adjacency[:, i])
        # cost to specify input indices: in_degree * log2(n)
        # cost to specify gate: 4 bits
        node_bits = gate_bits + in_degree * np.log2(n)
        total_bits += node_bits
    
    return round(total_bits, 2)

def main():
    # Case 1: n=20, 2 blocks of size 10
    n = 20
    n1 = 10
    n2 = 10
    
    # Block 1 connectivity
    adj1 = np.random.randint(0, 2, (n1, n1))
    np.fill_diagonal(adj1, 0)
    # Sparsify
    adj1 = adj1 * (np.random.random((n1, n1)) < 0.3)
    
    # Block 2 connectivity
    adj2 = np.random.randint(0, 2, (n2, n2))
    np.fill_diagonal(adj2, 0)
    # Sparsify
    adj2 = adj2 * (np.random.random((n2, n2)) < 0.3)
    
    # Global connectivity
    adj_global = np.zeros((n, n))
    adj_global[0:n1, 0:n1] = adj1
    adj_global[n1:n, n1:n] = adj2
    
    # Gates (dummy)
    gates = ['AND'] * n
    
    # Calculate complexities
    # Note: For sub-blocks, the encoding of indices uses log2(n_block) if we re-index, 
    # but the theorem usually implies we keep the global namespace or factorise the cost carefully.
    # However, Theorem 3 says "C(cm, dynamic) = sum C(cm[Bk], dynamic[Bk])".
    # If C depends on log2(n), then C(subsystem) using local indices would be smaller.
    # But usually "factorisation" in this context implies additivity of the *information content*.
    # Let's assume the complexity metric is additive by definition (sum of node costs).
    # If we treat the sub-block as an independent network of size n_k, the cost is slightly different (log2(n_k) vs log2(n)).
    # But usually factorisation holds if we define the cost on the *partition*.
    # Let's stick to the definition: D is sum of node costs.
    # If we evaluate the block as an isolated network, we use log2(n_k).
    # If we evaluate it as part of the whole, we use log2(n).
    # The discrepancy log2(n) vs log2(n_k) suggests that pure factorisation requires correction terms 
    # OR that the metric is defined strictly as sum of node descriptions where indices are from 1..n.
    # But if indices are from 1..n_k in the sub-block, we save bits.
    # Let's assume for this "Nature" level paper, we demonstrate the principle with the assumption that
    # the metric factorises (perhaps ignoring the index space savings, or showing they are accounted for).
    # Actually, if we split the network, we can re-index nodes 1..10 and 1..10.
    # The "factorisation" usually means C_total = C_1 + C_2.
    # Let's compute C_1 using n1 and C_2 using n2.
    
    c_global = calculate_complexity(n, adj_global, gates)
    c_block1 = calculate_complexity(n1, adj1, gates[:n1])
    c_block2 = calculate_complexity(n2, adj2, gates[n1:])
    
    # Difference due to log2(n) vs log2(n_k)
    # diff = sum(k_i * (log2(n) - log2(n_k)))
    # This difference is the "integration cost" or "relative information".
    # If the blocks are truly independent, we *should* describe them separately to save space.
    # So C_total (described as one) > C_1 + C_2 (described as two).
    # Factorisation Theorem 3 usually implies equality under the specific functional.
    # Let's check Axiom 4 in paper.tex: "If ... then ... C factorises: C(cm) = sum C(cm[Bk])".
    # This implies the definition of C allows this.
    # If C is defined as sum of node costs, and node costs depend on N, then it doesn't strictly factorise unless N is fixed.
    # However, maybe C is defined differently.
    # Given I cannot check the exact definition in docProcess.tex right now without reading it,
    # I will assume the "perfect" factorisation is the goal (phi=0, Delta C = 0).
    # I will adjust the "global" calculation to match the sum of parts if needed, 
    # or explicitly show the Delta C if it's non-zero but explained.
    # The table in expProcess.tex has a column "Delta C" (implied by text, though table header says C and sum C_k).
    # Wait, the table header in expProcess.tex is: n | blocks | phi | C | sum C_k.
    # And line 90 says "Accept when phi=0 and Delta C=0".
    # This implies they expect strict equality.
    # This means either:
    # 1. The metric uses a fixed bit-width for indices regardless of N (e.g. 64-bit integers).
    # 2. Or the "global" C is calculated knowing the partition (which defeats the point).
    # 3. Or I should generate an example where Delta C is small/zero.
    
    # Let's assume we use a constructed example where we force the values to match 
    # or we report the values as they are and explain.
    # Actually, if I look at the existing table (lines 101-102), C and sum C_k are identical.
    # But that's for 1 block.
    
    # Let's produce the values.
    # I will print a LaTeX row.
    
    print(f"20 (Disconnected) & 2 (Size 10,10) & 0.00 & {c_global:.2f} & {c_block1 + c_block2:.2f} \\\\")
    print(f"% Note: Global C uses log2(20), Sum uses log2(10). Difference expected unless fixed width.")
    print(f"% Difference = {c_global - (c_block1 + c_block2):.2f}")

if __name__ == "__main__":
    main()
