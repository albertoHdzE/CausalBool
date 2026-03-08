import numpy as np
import networkx as nx
from itertools import combinations
import math

class MotifEncoder:
    def __init__(self, adjacency_matrix):
        self.cm = np.array(adjacency_matrix)
        self.n = self.cm.shape[0]
        self.G = nx.from_numpy_array(self.cm, create_using=nx.DiGraph)
        
    def run(self):
        """
        Main execution method.
        """
        instances = self.find_motifs()
        motif_cost = self.compute_cost(instances)
        
        # Calculate residual cost (edges not in motifs)
        # 1. Identify all edges covered by motifs
        covered_edges = set()
        for m_type, motif_list in instances.items():
            for nodes in motif_list:
                subg = self.G.subgraph(nodes)
                for u, v in subg.edges():
                    covered_edges.add((u, v))
        
        # 2. Total edges
        all_edges = set(self.G.edges())
        
        # 3. Residual edges
        residual_edges = all_edges - covered_edges
        
        # 4. Residual cost: Simple edge list encoding
        # Each edge costs log2(N^2) = 2*log2(N)
        # Or log2(N*(N-1)) for directed without self-loops
        if self.n > 1:
            edge_cost_bits = math.log2(self.n * self.n)
        else:
            edge_cost_bits = 0
            
        residual_cost = len(residual_edges) * edge_cost_bits
        
        return {
            "instances": instances,
            "motif_cost": motif_cost,
            "residual_cost": residual_cost,
            "total_cost": motif_cost + residual_cost
        }

    def find_motifs(self):
        """
        Enumerate 3-node motifs.
        """
        instances = {
            "FFL": [],
            "FeedbackLoop": [],
            "Other": []
        }
        
        # Iterate over all 3-node combinations
        for nodes in combinations(range(self.n), 3):
            subg = self.G.subgraph(nodes)
            num_edges = subg.number_of_edges()
            
            if num_edges == 3:
                # Check for FFL vs Feedback
                if nx.is_directed_acyclic_graph(subg):
                    # FFL is a DAG with 3 edges (transitive triad)
                    instances["FFL"].append(nodes)
                else:
                    # Feedback loop (cycle of length 3)
                    # A cycle of 3 nodes with 3 edges is a feedback loop
                    # Need to verify it's a simple cycle
                    try:
                        cycles = list(nx.simple_cycles(subg))
                        if len(cycles) > 0 and len(cycles[0]) == 3:
                            instances["FeedbackLoop"].append(nodes)
                    except:
                        pass
                        
        return instances

    def compute_cost(self, instances):
        """
        Compute a description length cost based on motif frequency.
        Cost = Entropy_of_types + Location_cost
        """
        total_motifs = sum(len(v) for v in instances.values())
        if total_motifs == 0:
            return 0
            
        # Cost to specify "where" the motif is (3 nodes out of N)
        # log2(N choose 3)
        if self.n >= 3:
            n_choose_3 = math.comb(self.n, 3)
            location_cost = math.log2(n_choose_3)
        else:
            location_cost = 0
            
        # Shannon entropy of the motif distribution (Cost to specify "which" motif)
        type_entropy = 0
        for m_type, items in instances.items():
            count = len(items)
            if count > 0:
                p = count / total_motifs
                type_entropy -= p * math.log2(p)
                
        # Total bits
        # Sum over all motifs: (Location Cost + Type Entropy)
        return total_motifs * (location_cost + type_entropy)
